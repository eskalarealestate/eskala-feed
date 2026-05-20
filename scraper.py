import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import time
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_URL = "https://eskala.com.do"
AE_API_BASE = "https://secure.alterestate.com/api/v1"
AE_TOKEN = "dLE5FMsCkvRdsikMUodnY3v8GMxsLC6YdPG"

AGENCY_ID = "ESKALA-SRL"
AGENCY_NAME = "Eskala Real Estate"
AGENCY_EMAIL = "info@eskala.com.do"
AGENCY_PHONE = "+18099935000"
AGENCY_COUNTRY = "DO"
AGENCY_CITY = "Santo Domingo"
AGENT_ID = "EGENAO"
AGENT_NAME = "Edwin Genao Brito"
AGENT_EMAIL = "e.genao@eskala.com.do"
AGENT_PHONE = "+18099011002"

HEADERS = {
    "aetoken": AE_TOKEN,
    "User-Agent": "Mozilla/5.0",
}

# ============================================================
# OBTENER PROPIEDADES DESDE LA API DE ALTERESTATE
# ============================================================
def get_properties_from_api():
    """Obtiene todas las propiedades activas desde la API de AlterEstate"""
    all_properties = []
    page = 1

    while True:
        try:
            url = f"{AE_API_BASE}/properties/filter/?page={page}"
            print(f"  Obteniendo página {page}...")
            r = requests.get(url, headers=HEADERS, timeout=20)

            if r.status_code != 200:
                print(f"  API devolvió status {r.status_code} en página {page}. Fin.")
                break

            data = r.json()

            # La API puede devolver distintas estructuras
            results = (
                data.get("results") or
                data.get("properties") or
                data.get("data") or
                (data if isinstance(data, list) else [])
            )

            if not results:
                print(f"  Sin más resultados en página {page}.")
                break

            all_properties.extend(results)
            print(f"  Página {page}: {len(results)} propiedades (total: {len(all_properties)})")

            # Verificar si hay más páginas
            has_next = (
                data.get("next") or
                data.get("has_next") or
                (isinstance(results, list) and len(results) == 50)
            )
            if not has_next:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  Error en página {page}: {e}")
            break

    return all_properties


# ============================================================
# MAPEOS
# ============================================================
CITY_MAP = {
    "punta-cana": "Punta Cana", "punta cana": "Punta Cana",
    "bavaro": "Bávaro", "bávaro": "Bávaro",
    "cap-cana": "Cap Cana", "cap cana": "Cap Cana",
    "bayahibe": "Bayahibe",
    "santiago": "Santiago",
    "la-romana": "La Romana", "la romana": "La Romana",
    "las-terrenas": "Las Terrenas", "las terrenas": "Las Terrenas",
    "samana": "Samaná", "samaná": "Samaná",
    "jarabacoa": "Jarabacoa",
    "puerto-plata": "Puerto Plata", "puerto plata": "Puerto Plata",
    "cabarete": "Cabarete",
    "sosua": "Sosúa", "sosúa": "Sosúa",
    "juan-dolio": "Juan Dolio", "juan dolio": "Juan Dolio",
    "macao": "Macao",
    "vista-cana": "Punta Cana", "vista cana": "Punta Cana",
    "uvero-alto": "Punta Cana", "uvero alto": "Punta Cana",
    "downtown": "Punta Cana",
}

TYPE_MAP = {
    # villa
    "villa": "Villa",
    # apartment
    "apartamento": "Apartment", "apartment": "Apartment",
    "condo": "Apartment", "condominio": "Apartment",
    # house
    "casa": "House", "house": "House",
    "townhouse": "House", "town house": "House",
    "residencia": "House",
    # land
    "solar": "PlotOfLand", "terreno": "PlotOfLand", "plot": "PlotOfLand",
    # commercial
    "local": "Commercial", "comercial": "Commercial", "office": "Commercial",
}


def detect_city(text):
    text_lower = text.lower()
    for key, val in CITY_MAP.items():
        if key in text_lower:
            return val
    return "Santo Domingo"


def detect_subtype(text):
    text_lower = text.lower()
    for key, val in TYPE_MAP.items():
        if key in text_lower:
            return val
    return "Apartment"


def detect_advert_type(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["alquiler", "renta", "rent", "for rent"]):
        return "Rent"
    return "Sale"


def detect_bedrooms(text):
    text_lower = text.lower()
    # Busca patrones como "3 hab", "3 habitaciones", "3 bedrooms", "3br"
    patterns = [
        r'(\d+)\s*hab',
        r'(\d+)\s*bedroom',
        r'(\d+)\s*br\b',
        r'(\d+)\s*room',
    ]
    for pat in patterns:
        m = re.search(pat, text_lower)
        if m:
            return int(m.group(1))
    return 0


def get_property_detail(uid):
    """Obtiene el detalle completo de una propiedad por su uid, incluyendo todas las fotos"""
    try:
        url = f"{AE_API_BASE}/properties/{uid}/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        pass
    return None


def extract_images_from_api(prop):
    """Extrae URLs de imágenes de la respuesta de la API"""
    images = []

    # Campos comunes donde la API guarda imágenes
    image_fields = [
        "photos", "images", "pictures", "media",
        "gallery", "featured_image", "main_image",
        "photo", "image", "files", "attachments",
    ]

    for field in image_fields:
        val = prop.get(field)
        if not val:
            continue

        if isinstance(val, str) and val.startswith("http"):
            images.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.startswith("http"):
                    images.append(item)
                elif isinstance(item, dict):
                    for k in ["url", "src", "image", "photo", "path", "file", "original", "large"]:
                        img_url = item.get(k, "")
                        if img_url and img_url.startswith("http"):
                            images.append(img_url)
                            break
        elif isinstance(val, dict):
            for k in ["url", "src", "original", "large", "medium"]:
                img_url = val.get(k, "")
                if img_url and img_url.startswith("http"):
                    images.append(img_url)

    # También busca cualquier campo que contenga cloudfront
    for key, val in prop.items():
        if isinstance(val, str) and "cloudfront.net" in val and val not in images:
            images.append(val)

    # Eliminar logos de Eskala
    images = [
        img for img in images
        if "ESKALA" not in img and "LOGO" not in img and "logo" not in img.lower()
    ]

    return images[:20]


def parse_property(prop):
    """Convierte un objeto de la API al formato que necesitamos"""

    # ID / slug
    prop_id = (
        str(prop.get("id", "")) or
        prop.get("slug", "") or
        prop.get("reference", "")
    )

    # Slug para la URL pública
    slug = prop.get("slug", prop_id)
    url = f"{BASE_URL}/propiedad/{slug}" if slug else ""

    # Título
    title = (
        prop.get("title") or
        prop.get("name") or
        prop.get("titulo") or
        prop.get("nombre") or
        ""
    )
    # Si el título es un dict (por idiomas)
    if isinstance(title, dict):
        title = title.get("es") or title.get("en") or next(iter(title.values()), "")

    # Descripción
    description = (
        prop.get("description") or
        prop.get("descripcion") or
        prop.get("body") or
        prop.get("content") or
        ""
    )
    if isinstance(description, dict):
        description = description.get("es") or description.get("en") or next(iter(description.values()), "")

    # Limpiar HTML de la descripción
    description = re.sub(r'<[^>]+>', ' ', str(description)).strip()
    description = re.sub(r'\s+', ' ', description)
    if len(description) > 1000:
        description = description[:1000] + "..."

    # Precio
    price = 0
    for field in ["price", "precio", "sale_price", "rent_price", "amount"]:
        val = prop.get(field)
        if val:
            try:
                price = int(float(str(val).replace(",", "").replace("$", "").strip()))
                if price > 0:
                    break
            except:
                pass

    # Moneda
    currency = prop.get("currency", prop.get("moneda", "USD"))
    if not currency or currency not in ["USD", "EUR", "DOP"]:
        currency = "USD"

    # Tipo de operación
    advert_type = "Sale"
    op_field = prop.get("operation_type") or prop.get("tipo_operacion") or prop.get("listing_type") or ""
    if isinstance(op_field, dict):
        op_field = op_field.get("es") or op_field.get("en") or str(op_field)
    combined_text = f"{title} {str(op_field)}"
    advert_type = detect_advert_type(combined_text)

    # Subtipo
    type_field = prop.get("property_type") or prop.get("tipo_propiedad") or prop.get("type") or ""
    if isinstance(type_field, dict):
        type_field = type_field.get("es") or type_field.get("en") or str(type_field)
    sub_type = detect_subtype(f"{title} {str(type_field)} {slug}")

    # Ciudad
    location = prop.get("location") or prop.get("ciudad") or prop.get("city") or prop.get("sector") or ""
    if isinstance(location, dict):
        location = location.get("name") or location.get("es") or str(location)
    city = detect_city(f"{str(location)} {slug} {title}")

    # Habitaciones
    bedrooms = 0
    for field in ["bedrooms", "habitaciones", "rooms", "num_bedrooms"]:
        val = prop.get(field)
        if val:
            try:
                bedrooms = int(val)
                if bedrooms > 0:
                    break
            except:
                pass
    if bedrooms == 0:
        bedrooms = detect_bedrooms(title)

    # Imágenes
    images = extract_images_from_api(prop)

    return {
        "id": prop_id[:50],
        "url": url,
        "title": title or slug,
        "description": description or title or "Propiedad en venta en República Dominicana",
        "images": images,
        "price": price,
        "currency": currency,
        "advert_type": advert_type,
        "sub_type": sub_type,
        "city": city,
        "country": "DO",
        "bedrooms": bedrooms,
    }


# ============================================================
# FALLBACK: listado de slugs conocidos
# ============================================================
FALLBACK_SLUGS = [
    "villa-en-casa-de-campo-rancho-arriba","villa-renovada-con-amplio-jardin-en-santiago-villa-gonzalez",
    "apartamento-en-cap-cana-frente-al-campo-de-golf","apartamentos-con-vistas-al-mar-en-bayahibe",
    "apartamentos-de-lujo-con-confotur-en-cap-cana","apartamento-amueblado-en-jardines-iii-bavaro-punta-cana-en-venta",
    "apartamento-en-renta-en-bella-vista-santo-domingo","apartamento-de-2-habitaciones-de-venta-en-santiago",
    "apartamento-de-2-y-3-habitaciones-de-venta-en-santiago","apartamento-de-2-habitaciones-de-venta-en-evaristo-morales",
    "apartamento-amueblado-en-bayahibe","venta-de-apartamentos-listos-condo-hotel-en-naco-sd",
    "apartamentos-de-lujo-ubicado-en-el-sector-piantini-de-santo-domingo",
    "villas-duplex-de-dos-niveles-en-residencial-brisas-de-punta-cana","villa-con-3-habitaciones-en-punta-cana",
    "apartamento-en-la-esperilla-santo-domingo","condominio-hotelero-en-dominicus-bayahibe",
    "bayahibe-apartamentos-en-venta-caminando-a-la-playa",
    "apartamentos-100-amueblados-con-acceso-a-playa-privada-y-campo-de-golf",
    "apartamentos-de-2-y-3-habs-en-punta-cana",
    "punta-cana-venta-de-apartamentos-de-lujo-en-venta-en-downtown-punta-cana",
    "punta-cana-con-precios-de-oportunidad-apartamentos-de-1-2-y-3-habitaciones-en-downtown-punta-cana",
    "edificio-en-venta-en-el-corazon-de-santiago-ubicacion-privilegiada",
    "apartamentos-en-el-ensanche-evaristo-morales-santo-domingo",
    "villa-de-lujo-en-venta-en-casa-de-campo-la-romana",
    "villa-de-3-habitaciones-en-venta-en-punta-cana",
    "proyecto-residencial-exclusivo-en-playa-bonita-las-terrenas",
    "villa-de-3-habitaciones-en-venta-en-downtown-punta-cana","solar-en-jarabacoa-838395-m2",
    "villa-de-lujo-en-punta-cana-resort-and-club","villa-at-lagos-punta-cana",
    "apartamentos-y-villas-en-venta-en-white-sands-punta-cana","apartamento-en-alquiler-en-piantini",
    "apartamento-en-alquiler-de-lujo-en-bella-vista","apartamento-amueblado-en-piantini",
    "nuevo-desarrollo-en-los-rieles-de-gurabo-santiago",
    "apartamento-en-alquiler-en-evaristo-moralessanto-domingo",
    "villa-de-3-habitaciones-en-residencial-bavaro-punta-cana","apartamentos-de-lujo-en-venta-en-cap-cana",
    "apartments-island-houses-en-dominicus-bayahibe","apartamentos-en-cap-cana-en-venta",
    "proyecto-de-apartamentos-boutique-en-bayahibe","local-de-business-center-en-punta-cana",
    "villa-nueva-a-estrenar-en-ubicacion-privilegiada-en-punta-cana","apartamento-en-cap-cana",
    "apartamento-en-venta-en-bavaro","villa-en-venta-en-cap-cana",
    "apartamentos-en-venta-en-punta-cana-cana-bay-resort",
    "exclusivo-apartamento-en-venta-en-piantini-santo-domingo",
    "villa-lista-de-3-habitaciones-en-punta-cana","villa-en-venta-en-el-centro-de-punta-cana-ubicacion-exclusiva",
    "villa-exclusiva-de-3-habitaciones-en-el-centro-de-punta-cana",
    "apartamentos-de-1-2-y-3-habitaciones-en-jarabacoa-en-venta",
    "villa-de-3-habitaciones-en-bavaro-punta-cana",
    "villas-independientes-y-duplex-en-venta-en-punta-cana",
    "en-venta-apartamentos-beachfront-en-juan-dolio",
    "apartamentos-de-1-2-y-3-habitaciones-con-acceso-a-playa-bonita-las-terrenas",
    "townhouse-y-villas-en-venta-en-macao-punta-cana",
    "villa-de-5-habitaciones-en-venta-en-punta-cana-village",
    "villa-de-4-habitaciones-en-venta-en-punta-cana",
    "en-venta-en-cap-cana-exclusiva-villa-de-lujo-de-7-habitaciones",
    "en-venta-en-cap-cana-exclusiva-villa-de-lujo-de-6-habitaciones",
    "en-venta-en-cap-cana-exclusiva-villa-de-lujo-de-4-habitaciones",
    "en-venta-en-punta-cana-resort-exclusiva-villa-de-lujo-de-7-habitaciones",
    "exclusiva-villa-en-venta-en-punta-cana-village",
    "en-venta-en-cap-cana-villa-disenada-para-una-vida-de-lujo-e-inversion",
    "venta-de-apartamentos-de-lujo-en-bayahibe",
    "punta-cana-inversion-inmobiliaria-villa-en-venta-en-vista-cana",
    "proyecto-de-villa-de-inversion-inmobiliaria-en-vista-cana-punta-cana",
    "descubre-el-paraiso-en-marina-cap-cana","una-oportunidad-de-inversion-en-bavaro",
    "inversion-en-apartamentos-en-las-terrenas",
    "lujosa-townhouse-de-venta-en-dominicus-bayahibe",
    "venta-de-villa-de-lujo-con-finas-terminaciones-en-caleton-residences-en-cap-cana-punta-cana",
    "venta-de-villa-de-5-habs-en-caleton-residences-cap-cana-punta-cana",
    "villa-de-lujo-en-venta-en-caleton-residences-cap-cana-punta-cana",
    "venta-de-villa-con-4-o-5-habs-en-las-canas-cap-cana",
    "lujosa-villa-en-venta-en-ciudad-las-canas-cap-cana",
    "villa-golf-tipo-smarthome-de-venta-en-las-iguanas-cap-cana",
    "lujosa-villa-de-venta-en-las-iguanas-cap-cana-punta-cana",
    "lujosa-villa-en-caleton-residences-cap-cana-punta-cana",
    "hermosa-villa-en-venta-lista-para-mudarse-en-primaveral-2-punta-cana",
    "villas-en-venta-3-habitaciones-en-bavaro-punta-cana",
    "en-venta-bohochic-condo-hotel-en-down-town-punta-cana",
    "modernas-villas-akana-ciudad-las-canas","vistas-exclusivas-en-thomen-apartamentos-de-lujo-y-seguridad",
    "vive-la-modernidad-en-la-codiciada-thomen","ocean-view-apartments-at-the-marina-cap-cana",
    "golf-view-furnished-apartments-at-cabeza-de-toro","cap-cana-nuevo-desarrollo-a-precios-de-oportunidad",
    "alturas-de-lujo-6-torres-emblematicas-en-el-epicentro-urbano","riviera-bay-cana-bay-punta-cana",
    "jardines-iii-bavaro-punta-cana","exclusivo-complejo-de-villas-duplex-de-3-habitaciones-en-brisas-de-punta-cana",
    "desarrollo-de-lujo-en-downtown-punta-cana-con-apartmentos-de-1-y-2-habitaciones",
    "villa-de-4-habitaciones-en-el-village","residencia-en-punta-cana-village-lujo-comodidad-y-listo-para-mudarse",
    "villa-laguna-24-tranquilidad-lujo-y-diseno-exquisito","villa-107-lujo-y-elegancia-entrega-abril-2024-vista-al-campo-de-golf",
    "apartamentos-de-1-y-2-habitaciones-en-downtown-punta-cana",
    "cap-cana-nuevo-desarrollo-aptos-de-1-a-3-habitaciones-caminando-a-la-playa",
    "locales-comerciales-en-nueva-plaza-contemporanea-en-el-corazon-de-downtown-punta-cana",
    "apartamentos-en-punta-cana-caminando-a-la-playa",
    "discover-comfort-in-every-corner-of-the-exclusive-residential-complex-in-servalles",
    "experience-comfort-in-every-space-discover-the-new-complex-of-three-bedroom-villas-in-punta-cana",
    "1st-class-finishes-villas-with-3-bedrooms-and-open-layout",
    "caribbean-colonial-1-2-br-apartments-in-punta-cana",
    "3-bedroom-townhouses-with-patio-at-vista-cana",
    "private-gated-community-of-50-detached-villas-fully-equipped-kitchen",
    "nuevo-desarrollo-de-apartamentos-en-arroyo-hondo-santo-domingo",
    "super-precios-apartamentos-de-2-habitaciones-en-bayahibe",
    "hermosas-villas-en-playa-macao","luxury-apartments-in-vista-cana-affordable-prices",
    "luxury-gated-community-with-villas-and-condos-in-vista-cana",
    "tropical-design-apartments-in-vista-cana","stunning-luxury-3-bedrooms-villas-in-vista-cana",
    "modern-villas-at-downtown-punta-cana","2-3-bedrooms-townhouses-in-los-corales-punta-cana",
    "luxury-residential-tower-in-serralles-santo-domingo",
    "investment-apartments-in-santo-domingo-strategic-location",
    "1-2-rooms-apartments-in-vista-cana-invest-safely",
    "stunning-4-bedrooms-villa-in-punta-cana-resorts-club",
    "luxury-and-tropical-5-rooms-villa-in-punta-cana-resorts",
    "4-bedrooms-villa-in-punta-cana-villa","stunning-apartments-in-cap-cana",
    "luxury-apartments-in-vista-cana-affordable-prices",
    "beautiful-apartments-in-the-marina-cap-cana","new-apartments-in-cocotal-golf-country-club",
    "villas-and-apartments-walking-distance-to-the-beach",
    "apartments-and-villas-walking-distance-to-portillo-beach-las-terrenas",
    "apartments-walking-distance-to-the-beach-at-los-corales",
    "luxury-condos-with-artificial-beach-confotur-and-appliances-included",
    "opportunity-prices-1-to-2-rooms-apartments-in-punta-cana",
    "amplios-y-exclusivos-apartamentos-en-los-cacigazcos",
    "apartments-in-cap-cana-golf-course-views","luxury-villas-in-vista-cana",
    "invierte-en-esta-torre-residencial-en-el-corazon-de-piantini",
    "confortable-and-spacious1-bedroom-2-bathrooms-apartment-in-a-gated-complex-with-a-pool",
    "exclusive-3-bedroom-villa-complex-with-pool-in-whitesands",
    "4-min-to-the-beach-beautiful-2-bedrooms-apartment-in-las-terrenas-samana",
    "nuevo-desarrollo-de-apartamentos-en-arroyo-hondo-santo-domingo",
]


def get_fallback_properties():
    """Genera propiedades básicas a partir de los slugs conocidos"""
    props = []
    for slug in FALLBACK_SLUGS:
        url = f"{BASE_URL}/propiedad/{slug}"
        title = slug.replace("-", " ").title()
        props.append({
            "id": slug[:50],
            "url": url,
            "title": title,
            "description": f"Propiedad en venta en República Dominicana. {title}.",
            "images": [],
            "price": 0,
            "currency": "USD",
            "advert_type": detect_advert_type(slug),
            "sub_type": detect_subtype(slug),
            "city": detect_city(slug),
            "country": "DO",
            "bedrooms": detect_bedrooms(slug),
        })
    return props


# ============================================================
# GENERAR XML EN FORMATO PROPERSTAR 2025
# ============================================================
def generate_xml(properties):
    root = ET.Element("ListingExport")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    contact = ET.SubElement(root, "Contact")

    office = ET.SubElement(contact, "Office")
    ET.SubElement(office, "OfficeOriginalId").text = AGENCY_ID
    ET.SubElement(office, "CorporateName").text = AGENCY_NAME
    ET.SubElement(office, "Email").text = AGENCY_EMAIL
    ET.SubElement(office, "LandPhone").text = AGENCY_PHONE
    ET.SubElement(office, "Country").text = AGENCY_COUNTRY
    ET.SubElement(office, "City").text = AGENCY_CITY
    ET.SubElement(office, "Website").text = "https://eskala.com.do"

    agent = ET.SubElement(contact, "Agent")
    ET.SubElement(agent, "AgentId").text = AGENT_ID
    ET.SubElement(agent, "FullName").text = AGENT_NAME
    ET.SubElement(agent, "AgentEmail").text = AGENT_EMAIL
    ET.SubElement(agent, "MobilePhone").text = AGENT_PHONE
    ET.SubElement(agent, "Country").text = "DO"

    adverts = ET.SubElement(root, "Adverts")

    for prop in properties:
        if not prop:
            continue

        advert = ET.SubElement(adverts, "Advert")
        ET.SubElement(advert, "AdvertId").text = str(prop["id"])[:50]
        ET.SubElement(advert, "OriginalUrl").text = prop["url"]
        ET.SubElement(advert, "AdvertType").text = prop["advert_type"]
        ET.SubElement(advert, "SubType").text = prop["sub_type"]
        ET.SubElement(advert, "Status").text = "Active"
        ET.SubElement(advert, "PublicationDate").text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        if prop.get("bedrooms", 0) > 0:
            ET.SubElement(advert, "Bedrooms").text = str(prop["bedrooms"])

        descs = ET.SubElement(advert, "Descriptions")
        desc_el = ET.SubElement(descs, "Description")
        desc_el.set("Language", "es")
        desc_el.text = prop["description"]

        titles_el = ET.SubElement(advert, "Titles")
        title_el = ET.SubElement(titles_el, "Title")
        title_el.set("Language", "es")
        title_el.text = prop["title"]

        price = prop.get("price", 0)
        ET.SubElement(advert, "Price").text = str(price)
        ET.SubElement(advert, "PriceCurrency").text = prop.get("currency", "USD")
        ET.SubElement(advert, "ShowPrice").text = "1" if price > 0 else "0"

        ET.SubElement(advert, "Country").text = "DO"
        ET.SubElement(advert, "City").text = prop["city"]
        ET.SubElement(advert, "PostalCode").text = "00000"

        images = prop.get("images", [])
        if images:
            photos = ET.SubElement(advert, "Photos")
            for img_url in images[:20]:
                ET.SubElement(photos, "Photo").text = img_url

    xml_str = ET.tostring(root, encoding="unicode")
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  ", encoding="UTF-8").decode("UTF-8")


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"[{datetime.now()}] Iniciando generación de feed Properstar...")

    print("\n--- Intentando API de AlterEstate ---")
    raw_properties = get_properties_from_api()

    properties = []
    if raw_properties:
        print(f"\nProcesando {len(raw_properties)} propiedades de la API...")

        # Debug: claves del listado
        first = raw_properties[0]
        print(f"  Claves disponibles en API (listado): {list(first.keys())}")

        # Obtener detalle de la primera propiedad para ver todas las claves
        first_uid = first.get("uid") or first.get("id") or first.get("cid") or ""
        if first_uid:
            first_detail = get_property_detail(first_uid)
            if first_detail:
                print(f"  Claves disponibles en API (detalle): {list(first_detail.keys())}")

        # Procesar cada propiedad obteniendo su detalle completo
        for i, raw in enumerate(raw_properties):
            uid = raw.get("uid") or raw.get("id") or raw.get("cid") or ""
            detail = None
            if uid:
                detail = get_property_detail(uid)
                time.sleep(0.1)
            prop = parse_property(detail if detail else raw)
            properties.append(prop)
            if (i + 1) % 50 == 0:
                print(f"  Procesadas {i+1}/{len(raw_properties)}...")
    else:
        print("\nAPI no disponible. Usando listado de respaldo...")
        properties = get_fallback_properties()

    print(f"\nTotal propiedades en feed: {len(properties)}")

    # Estadísticas
    with_images = sum(1 for p in properties if p.get("images"))
    with_price = sum(1 for p in properties if p.get("price", 0) > 0)
    print(f"  Con imágenes: {with_images}")
    print(f"  Con precio: {with_price}")

    xml_content = generate_xml(properties)

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"\nFeed generado: feed.xml")
    print(f"URL pública: https://eskalarealestate.github.io/eskala-feed/feed.xml")


if __name__ == "__main__":
    main()

import requests
from bs4 import BeautifulSoup
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

API_HEADERS = {
    "aetoken": AE_TOKEN,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ============================================================
# MAPEOS
# ============================================================
CITY_MAP = {
    "punta cana": "Punta Cana", "punta-cana": "Punta Cana",
    "bavaro": "Bávaro", "bávaro": "Bávaro",
    "cap cana": "Cap Cana", "cap-cana": "Cap Cana",
    "bayahibe": "Bayahibe",
    "santiago": "Santiago",
    "la romana": "La Romana", "la-romana": "La Romana",
    "las terrenas": "Las Terrenas", "las-terrenas": "Las Terrenas",
    "samana": "Samaná", "samaná": "Samaná",
    "jarabacoa": "Jarabacoa",
    "puerto plata": "Puerto Plata", "puerto-plata": "Puerto Plata",
    "cabarete": "Cabarete",
    "sosua": "Sosúa", "sosúa": "Sosúa",
    "juan dolio": "Juan Dolio", "juan-dolio": "Juan Dolio",
    "macao": "Macao",
    "vista cana": "Punta Cana", "vista-cana": "Punta Cana",
    "uvero alto": "Punta Cana", "uvero-alto": "Punta Cana",
    "downtown": "Punta Cana",
    "santo domingo": "Santo Domingo",
}

TYPE_MAP = {
    "villa": "Villa",
    "apartamento": "Apartment", "apartment": "Apartment",
    "condo": "Apartment", "condominio": "Apartment",
    "penthouse": "Apartment",
    "casa": "House", "house": "House",
    "townhouse": "House", "town house": "House",
    "residencia": "House",
    "solar": "PlotOfLand", "terreno": "PlotOfLand", "plot": "PlotOfLand",
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
    for pat in [r'(\d+)\s*hab', r'(\d+)\s*bedroom', r'(\d+)\s*br\b', r'(\d+)\s*room']:
        m = re.search(pat, text_lower)
        if m:
            return int(m.group(1))
    return 0


# ============================================================
# PASO 1: OBTENER PROPIEDADES DE LA API
# ============================================================
def get_properties_from_api():
    all_properties = []
    page = 1

    while True:
        try:
            url = f"{AE_API_BASE}/properties/filter/?page={page}"
            print(f"  Página {page}...")
            r = requests.get(url, headers=API_HEADERS, timeout=20)

            if r.status_code != 200:
                print(f"  Status {r.status_code}, fin de paginación.")
                break

            data = r.json()
            results = (
                data.get("results") or
                data.get("properties") or
                data.get("data") or
                (data if isinstance(data, list) else [])
            )

            if not results:
                break

            all_properties.extend(results)
            print(f"  Página {page}: {len(results)} propiedades (total: {len(all_properties)})")

            has_next = (
                data.get("next") or
                data.get("has_next") or
                (isinstance(results, list) and len(results) >= 30)
            )
            if not has_next:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"  Error en página {page}: {e}")
            break

    return all_properties



# ============================================================
# OBTENER AGENTES DESDE LA API
# ============================================================
def get_agents():
    """Obtiene todos los agentes y construye un mapa nombre -> datos"""
    agents_map = {}
    try:
        r = requests.get(f"{AE_API_BASE}/agents/", headers=API_HEADERS, timeout=15)
        if r.status_code == 200:
            agents_list = r.json()
            if isinstance(agents_list, list):
                for agent in agents_list:
                    full_name = agent.get("full_name", "").strip()
                    if full_name:
                        agents_map[full_name] = {
                            "id": agent.get("slug", str(agent.get("id", ""))),
                            "name": full_name,
                            "email": agent.get("email", ""),
                            "phone": agent.get("phone", ""),
                            "position": agent.get("position", ""),
                        }
                print(f"  Agentes cargados: {list(agents_map.keys())}")
    except Exception as e:
        print(f"  Error cargando agentes: {e}")
    return agents_map


# ============================================================
# PASO 2: SCRAPING DE FOTOS DESDE LA PÁGINA WEB
# ============================================================
def scrape_photos(url):
    """Visita la página de la propiedad y extrae todas las fotos reales"""
    try:
        r = requests.get(url, headers=SCRAPE_HEADERS, timeout=15)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")

        # Verificar que no es página de error
        page_text = soup.get_text()
        if "página que estás buscando no existe" in page_text or "no existe o ha sido movida" in page_text:
            return []

        images = []

        # Buscar todas las imágenes de cloudfront (fotos reales de propiedades)
        for img in soup.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "") or img.get("data-lazy-src", "")
            if "d2kflbb1pmooh4.cloudfront.net" in src:
                if src not in images:
                    images.append(src)

        # También buscar en atributos style y backgrounds
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            urls = re.findall(r'url\(["\']?(https://d2kflbb1pmooh4\.cloudfront\.net[^"\')\s]+)', style)
            for u in urls:
                if u not in images:
                    images.append(u)

        # Buscar en scripts JSON (galerías cargadas con JS)
        for script in soup.find_all("script"):
            script_text = script.string or ""
            urls = re.findall(r'https://d2kflbb1pmooh4\.cloudfront\.net/[^\s"\'\\]+', script_text)
            for u in urls:
                if u not in images:
                    images.append(u)

        # Filtrar logos de Eskala
        images = [
            img for img in images
            if "ESKALA" not in img and "LOGO" not in img and "logo" not in img.lower()
            and "static/companies" not in img and "static/user" not in img
        ]

        return images[:20]

    except Exception as e:
        return []


# ============================================================
# PASO 3: COMBINAR DATOS DE API + FOTOS
# ============================================================
def build_property(raw, photos, agents_map=None):
    """Construye el objeto propiedad combinando datos de la API y fotos del scraping"""

    slug = raw.get("slug", "")
    uid = raw.get("uid", raw.get("cid", ""))
    prop_id = str(uid) if uid else slug

    url = f"{BASE_URL}/propiedad/{slug}" if slug else ""

    # Título — buscar en translations primero
    title = ""
    translations = raw.get("translations", {})
    if isinstance(translations, dict):
        for lang in ["es", "en"]:
            t = translations.get(lang, {})
            if isinstance(t, dict):
                title = t.get("name") or t.get("title") or ""
                if title:
                    break
    if not title:
        title = raw.get("name", slug.replace("-", " ").title() if slug else "")

    # Descripción
    description = ""
    if isinstance(translations, dict):
        for lang in ["es", "en"]:
            t = translations.get(lang, {})
            if isinstance(t, dict):
                description = t.get("short_description") or t.get("description") or ""
                if description:
                    break
    if not description:
        description = raw.get("short_description", "")
    description = re.sub(r'<[^>]+>', ' ', str(description)).strip()
    description = re.sub(r'\s+', ' ', description)
    if not description:
        description = title

    # Precio
    price = 0
    currency = "USD"
    condition = raw.get("condition", "sale")
    if "rent" in str(condition).lower():
        price_raw = raw.get("rent_price") or raw.get("rental_price") or 0
    else:
        price_raw = raw.get("sale_price") or raw.get("furnished_sale_price") or 0

    try:
        price = int(float(str(price_raw).replace(",", "")))
    except:
        price = 0

    # Moneda
    if "rent" in str(condition).lower():
        currency = raw.get("currency_rent", "USD") or "USD"
    else:
        currency = raw.get("currency_sale", "USD") or "USD"
    if currency not in ["USD", "EUR", "DOP"]:
        currency = "USD"

    # Tipo de operación
    advert_type = "Rent" if "rent" in str(condition).lower() else "Sale"

    # Subtipo — usar category de la API
    category = raw.get("category", "")
    if isinstance(category, dict):
        category = category.get("name") or category.get("es") or str(category)
    sub_type = detect_subtype(f"{str(category)} {title} {slug}")

    # Ciudad — usar city/province/sector de la API
    city_api = raw.get("city", "") or raw.get("province", "") or raw.get("sector", "")
    if isinstance(city_api, dict):
        city_api = city_api.get("name") or city_api.get("es") or str(city_api)
    city = detect_city(f"{str(city_api)} {slug}")

    # Habitaciones
    bedrooms = 0
    try:
        bedrooms = int(raw.get("room", 0) or 0)
    except:
        pass
    if bedrooms == 0:
        bedrooms = detect_bedrooms(title)


    # Área de la propiedad
    living_area = 0
    living_area_unit = "sqm"
    try:
        living_area = float(raw.get("property_area", 0) or 0)
        measurer = str(raw.get("property_area_measurer", "m2")).lower()
        if "ft" in measurer:
            living_area_unit = "sqft"
    except:
        pass

    plot_area = 0
    plot_area_unit = "sqm"
    try:
        plot_area = float(raw.get("terrain_area", 0) or 0)
        measurer = str(raw.get("terrain_area_measurer", "m2")).lower()
        if "ft" in measurer:
            plot_area_unit = "sqft"
    except:
        pass

    # Fotos: usar las del scraping, fallback a featured_image_original (URL pública)
    images = photos
    if not images:
        parent = raw.get("parent", {}) or {}
        original = parent.get("featured_image_original", "")
        if original and original.startswith("http"):
            images = [original]
        else:
            featured = raw.get("featured_image", "")
            if featured and featured.startswith("http"):
                if "ESKALA" not in featured and "LOGO" not in featured:
                    images = [featured]

    # Agente asignado a esta propiedad
    agent_data = {}
    if agents_map:
        agent_names = raw.get("agents", [])
        if agent_names and isinstance(agent_names, list):
            agent_name = agent_names[0]
            agent_data = agents_map.get(agent_name, {})

    return {
        "id": prop_id,
        "url": url,
        "title": title,
        "description": description,
        "images": images,
        "price": price,
        "currency": currency,
        "advert_type": advert_type,
        "sub_type": sub_type,
        "city": city,
        "country": "DO",
        "bedrooms": bedrooms,
        "living_area": int(living_area) if living_area > 0 else 0,
        "living_area_unit": living_area_unit,
        "plot_area": int(plot_area) if plot_area > 0 else 0,
        "plot_area_unit": plot_area_unit,
        "agent": agent_data,
    }


# ============================================================
# GENERAR XML PROPERSTAR 2025
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

        if prop.get("living_area", 0) > 0:
            ET.SubElement(advert, "LivingArea").text = str(prop["living_area"])
            ET.SubElement(advert, "LivingAreaUnit").text = prop.get("living_area_unit", "sqm")

        if prop.get("plot_area", 0) > 0:
            ET.SubElement(advert, "PlotArea").text = str(prop["plot_area"])
            ET.SubElement(advert, "PlotAreaUnit").text = prop.get("plot_area_unit", "sqm")

        images = prop.get("images", [])
        if images:
            photos_el = ET.SubElement(advert, "Photos")
            for img_url in images:
                ET.SubElement(photos_el, "Photo").text = img_url

        # Agente por propiedad
        agent = prop.get("agent", {})
        if agent and agent.get("name"):
            listing_contact = ET.SubElement(advert, "ListingContact")
            ET.SubElement(listing_contact, "ContactId").text = str(agent.get("id", ""))
            ET.SubElement(listing_contact, "ContactName").text = agent.get("name", "")
            if agent.get("email"):
                ET.SubElement(listing_contact, "ContactEmail").text = agent["email"]
            if agent.get("phone"):
                ET.SubElement(listing_contact, "ContactPhone").text = agent["phone"]

    xml_str = ET.tostring(root, encoding="unicode")
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  ", encoding="UTF-8").decode("UTF-8")


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"[{datetime.now()}] Iniciando generación de feed Properstar...")

    # Paso 1: obtener todas las propiedades de la API
    print("\n--- Paso 1: API de AlterEstate ---")
    raw_properties = get_properties_from_api()
    print(f"Total propiedades en API: {len(raw_properties)}")

    if not raw_properties:
        print("ERROR: No se pudieron obtener propiedades de la API.")
        return



    # Cargar agentes
    print("\n--- Cargando agentes ---")
    agents_map = get_agents()

    # Paso 2: scraping de fotos + construcción de propiedades
    print("\n--- Paso 2: Scraping de fotos ---")
    properties = []
    no_photos = 0

    for i, raw in enumerate(raw_properties):
        slug = raw.get("slug", "")
        url = f"{BASE_URL}/propiedad/{slug}"

        photos = []
        if slug:
            photos = scrape_photos(url)
            time.sleep(0.3)

        prop = build_property(raw, photos, agents_map)
        properties.append(prop)

        if not photos:
            no_photos += 1

        if (i + 1) % 50 == 0:
            print(f"  Procesadas {i+1}/{len(raw_properties)} | Sin fotos: {no_photos}")

    # Estadísticas finales
    with_photos = sum(1 for p in properties if p.get("images"))
    with_price = sum(1 for p in properties if p.get("price", 0) > 0)
    avg_photos = sum(len(p.get("images", [])) for p in properties) / len(properties) if properties else 0

    print(f"\n--- Resultado ---")
    print(f"  Total propiedades: {len(properties)}")
    print(f"  Con fotos: {with_photos}")
    print(f"  Sin fotos: {len(properties) - with_photos}")
    print(f"  Con precio: {with_price}")
    print(f"  Promedio fotos por propiedad: {avg_photos:.1f}")

    # Generar XML
    xml_content = generate_xml(properties)
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"\nFeed generado: feed.xml")
    print(f"URL pública: https://eskalarealestate.github.io/eskala-feed/feed.xml")


if __name__ == "__main__":
    main()

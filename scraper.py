import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import re
import time
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_URL = "https://eskala.com.do"
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ============================================================
# OBTENER LISTADO DE PROPIEDADES
# ============================================================
def get_property_urls():
    """Intenta obtener URLs desde la API de AlterEstate, si falla usa listado de respaldo"""
    urls = []
    page = 1
    while True:
        try:
            api_url = f"{BASE_URL}/api/properties?page={page}&per_page=50"
            r = requests.get(api_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            properties = data.get("results", data.get("properties", []))
            if not properties:
                break
            for prop in properties:
                slug = prop.get("slug", "")
                if slug:
                    urls.append(f"{BASE_URL}/propiedad/{slug}")
            if not data.get("next"):
                break
            page += 1
            time.sleep(1)
        except Exception as e:
            print(f"API no disponible (página {page}): {e}")
            break

    if not urls:
        print("Usando listado de respaldo...")
        urls = get_fallback_urls()

    print(f"Total propiedades a procesar: {len(urls)}")
    return urls


def get_fallback_urls():
    """Listado de respaldo con los 276 slugs conocidos"""
    slugs = [
        "villa-en-casa-de-campo-rancho-arriba",
        "villa-renovada-con-amplio-jardin-en-santiago-villa-gonzalez",
        "apartamento-en-cap-cana-frente-al-campo-de-golf",
        "apartamentos-con-vistas-al-mar-en-bayahibe",
        "apartamentos-de-lujo-con-confotur-en-cap-cana",
        "apartamento-amueblado-en-jardines-iii-bavaro-punta-cana-en-venta",
        "apartamento-en-renta-en-bella-vista-santo-domingo",
        "apartamento-de-2-habitaciones-de-venta-en-santiago",
        "apartamento-de-2-y-3-habitaciones-de-venta-en-santiago",
        "apartamento-de-2-habitaciones-de-venta-en-evaristo-morales",
        "apartamento-amueblado-en-bayahibe",
        "venta-de-apartamentos-listos-condo-hotel-en-naco-sd",
        "apartamentos-de-lujo-ubicado-en-el-sector-piantini-de-santo-domingo",
        "villas-duplex-de-dos-niveles-en-residencial-brisas-de-punta-cana",
        "villa-con-3-habitaciones-en-punta-cana",
        "apartamento-en-la-esperilla-santo-domingo",
        "condominio-hotelero-en-dominicus-bayahibe",
        "bayahibe-apartamentos-en-venta-caminando-a-la-playa",
        "apartamentos-100-amueblados-con-acceso-a-playa-privada-y-campo-de-golf",
        "apartamentos-de-2-y-3-habs-en-punta-cana",
        "punta-cana-venta-de-apartamentos-de-lujo-en-venta-en-downtown-punta-cana",
        "punta-cana-con-precios-de-oportunidad-apartamentos-de-1-2-y-3-habitaciones-en-downtown-punta-cana",
        "edificio-en-venta-en-el-corazon-de-santiago-ubicacion-privilegiada",
        "apartamentos-en-el-ensanche-evaristo-morales-santo-domingo",
        "villa-de-lujo-en-venta-en-casa-de-campo-la-romana",
        "casa-en-venta-en-santiago-urbanizacion-pradera-del-cerro-vista-de-cerro-alto",
        "villa-de-3-habitaciones-en-venta-en-punta-cana",
        "proyecto-residencial-exclusivo-en-playa-bonita-las-terrenas",
        "villa-de-3-habitaciones-en-venta-en-downtown-punta-cana",
        "solar-en-jarabacoa-838395-m2",
        "villa-de-lujo-en-punta-cana-resort-and-club",
        "villa-at-lagos-punta-cana",
        "apartamentos-y-villas-en-venta-en-white-sands-punta-cana",
        "apartamento-en-alquiler-en-piantini",
        "apartamento-en-alquiler-de-lujo-en-bella-vista",
        "apartamento-amueblado-en-piantini",
        "nuevo-desarrollo-en-los-rieles-de-gurabo-santiago",
        "apartamento-en-alquiler-en-evaristo-moralessanto-domingo",
        "villa-de-3-habitaciones-en-residencial-bavaro-punta-cana",
        "apartamentos-de-lujo-en-venta-en-cap-cana",
        "apartments-island-houses-en-dominicus-bayahibe",
        "apartamentos-en-cap-cana-en-venta",
        "proyecto-de-apartamentos-boutique-en-bayahibe",
        "local-de-business-center-en-punta-cana",
        "apartamento-en-venta-en-cerros-de-gurabo-iii-santiago",
        "villa-nueva-a-estrenar-en-ubicacion-privilegiada-en-punta-cana",
        "apartamento-en-cap-cana",
        "apartamento-en-venta-en-bavaro",
        "exclusivo-apartamentos-en-vistacana-de-2-y-3-habitaciones",
        "apartamentos-modernos-con-areas-recreativas-en-vista-cana-punta-cana",
        "villa-en-venta-en-cap-cana",
        "apartamentos-en-venta-en-punta-cana-cana-bay-resort",
        "proyecto-de-apartamentos-frente-a-la-playa",
        "apartamento-en-en-la-hermosa-playa-de-uvero-alto-punta-cana",
        "exclusivo-apartamento-en-venta-en-piantini-santo-domingo",
        "villa-amueblada-con-piscina-y-rooftop",
        "villa-lista-de-3-habitaciones-en-punta-cana",
        "en-venta-villa-de-lujo-en-residencial-bavaro-punta-cana",
        "villa-en-venta-en-el-centro-de-punta-cana-ubicacion-exclusiva",
        "villa-exclusiva-de-3-habitaciones-en-el-centro-de-punta-cana",
        "venta-de-apartamentos-de-1-y-2-habitaciones-en-exclusivo-sector-ensanche-naco",
        "en-venta-elegantes-apartamentos-de-1-y-2-habitaciones-en-naco",
        "apartamentos-de-1-2-y-3-habitaciones-en-jarabacoa-en-venta",
        "apartamentos-de-1-2-y-3-habitaciones-en-venta-en-coral-golf-resort-cabeza-de-toro",
        "venta-de-apartamento-tipo-condo-hotel-en-el-sector-la-julia",
        "apartamento-de-3-habitaciones-mas-estudio-en-naco-santo-domingo",
        "villa-de-3-habitaciones-en-bavaro-punta-cana",
        "villas-independientes-y-duplex-en-venta-en-punta-cana",
        "en-venta-apartamentos-beachfront-en-juan-dolio",
        "apartamentos-de-1-2-y-3-habitaciones-con-acceso-a-playa-bonita-las-terrenas",
        "townhouse-y-villas-en-venta-en-macao-punta-cana",
        "exclusivo-residencial-en-puerto-plata-frente-a-playa-dorada",
        "exclusiva-torre-residencial-en-santiago-apartamentos-en-venta",
        "apartamento-de-2-y-3-habitaciones-de-venta-en-santiago",
        "villa-de-5-habitaciones-en-venta-en-punta-cana-village",
        "venta-de-villas-4-habitaciones-en-punta-cana-theme-park-resort",
        "villa-de-4-habitaciones-en-venta-en-punta-cana",
        "villa-de-3-habitaciones-en-venta-en-punta-cana-san-juan-lakes",
        "en-venta-en-cap-cana-exclusiva-villa-de-lujo-de-7-habitaciones",
        "en-venta-en-cap-cana-exclusiva-villa-de-lujo-de-6-habitaciones",
        "en-venta-en-cap-cana-exclusiva-villa-de-lujo-de-4-habitaciones",
        "en-venta-en-punta-cana-resort-exclusiva-villa-de-lujo-de-7-habitaciones",
        "exclusiva-villa-en-venta-en-punta-cana-village",
        "en-venta-en-cap-cana-villa-disenada-para-una-vida-de-lujo-e-inversion",
        "vive-con-lujo-residencias-exclusivas-en-cana-bay-punta-cana",
        "venta-de-apartamentos-de-lujo-en-bayahibe",
        "espacios-amplios-y-confort-inigualable-penthouse-en-venta-en-el-renacimiento",
        "punta-cana-inversion-inmobiliaria-villa-en-venta-en-vista-cana",
        "apartamento-en-venta-en-la-julia-santo-domingo-3-habitaciones",
        "proyecto-de-villa-de-inversion-inmobiliaria-en-vista-cana-punta-cana",
        "descubre-el-paraiso-en-marina-cap-cana",
        "una-oportunidad-de-inversion-en-bavaro",
        "inversion-en-apartamentos-en-las-terrenas",
        "lujosa-townhouse-de-venta-en-dominicus-bayahibe",
        "venta-de-villa-de-lujo-con-finas-terminaciones-en-caleton-residences-en-cap-cana-punta-cana",
        "venta-de-villa-de-5-habs-en-caleton-residences-cap-cana-punta-cana",
        "villa-de-lujo-en-venta-en-caleton-residences-cap-cana-punta-cana",
        "venta-de-villa-de-lujo-de-2-niv-con-piscina-en-punta-cana-village-punta-cana",
        "venta-de-villa-con-4-o-5-habs-en-las-canas-cap-cana",
        "venta-de-villa-de-6-habs-de-lujo-en-caleton-residences-cap-cana-punta-cana",
        "venta-de-villa-en-caleton-residences-cap-cana-punta-cana",
        "lujosa-villa-en-venta-en-ciudad-las-canas-cap-cana",
        "venta-de-villa-en-planos-en-residencial-del-parque-cap-cana-punta-cana",
        "villa-golf-tipo-smarthome-de-venta-en-las-iguanas-cap-cana",
        "lujosa-villa-de-venta-en-las-iguanas-cap-cana-punta-cana",
        "lujosa-villa-en-caleton-residences-cap-cana-punta-cana",
        "hermosa-villa-en-venta-lista-para-mudarse-en-primaveral-2-punta-cana",
        "villas-en-venta-3-habitaciones-en-bavaro-punta-cana",
        "en-venta-bohochic-condo-hotel-en-down-town-punta-cana",
        "en-venta-apartamentos-1-y-2-habitaciones-en-frente-al-campo-de-golf-en-cocotal",
        "completamente-amueblado-1-y-2-habitaciones-a-8-minutos-de-la-playa-punta-cana",
        "apartamentos-de-1-2-y-3-habitaciones-en-pueblo-bavaroo",
        "villas-2-3-habitaciones-en-veron",
        "villa-duplex-de-3-habitaciones-en-down-town",
        "invierte-en-un-condo-hotel-de-lujo-en-punta-cana",
        "15-exclusivas-villas-de-3-habitaciones-en-vista-cana-vista-cana",
        "apartamentos-de-lujo-con-opciones-de-1-2-y-3-habitaciones-situados-en-el-exclusivo-coral-golf-resort",
        "villas-de-3-y-4-habitaciones-en-el-corazon-de-vista-cana",
        "apartamentos-de-lujo-en-venta-en-santiago",
        "a-solo-pasos-de-la-playa-donde-el-lujo-y-la-naturalezase-encuentran",
        "vive-a-solo-pasos-de-la-playa-unidades-de-1-y-2-habitaciones",
        "apartamentos-de-lujo-en-naco-2-y-3-habitaciones",
        "apartamentos-1-2-y-3-hab-en-venta-vista-cana-tu-nuevo-hogar",
        "ultimas-unidades-villas-de-3-habitaciones-y-3-banos-en-venta-en-bavaro",
        "cap-cana-de-lujo-123-habitaciones-con-confotur",
        "cap-cana-1-3-habitaciones-con-confotur",
        "nuevos-apartamentos-en-venta-en-vista-cana-mejor-precio-en-la-zona",
        "cap-cana-nuevo-desarrollo-con-apartamentos-en-venta-2-y-3-dormitorios",
        "villa-lista-con-5-habitaciones-en-venta-en-punta-cana-village",
        "bayahibe-caminando-a-la-playa-nuevo-desarrollo-con-entrega-en-2027",
        "nuevo-complejo-en-punta-cana-apartmentos",
        "for-sale-2br-apartment-ocean-view-at-playa-laguna-sosua-puerto-plata",
        "tu-paraiso-te-espera-apartamentos-listos-a-solo-8-minutos-de-la-playa-el-cortecito",
        "apartamentos-de-2-y-3-habitaciones-en-gurabo-con-fideicomiso",
        "capcana-apartamentos-exclusivos-en-ciudad-las-canas",
        "apartamento-de-2-habitaciones-costa-bavaro-garden-acceso-a-playa",
        "villa-tropical-en-cap-cana-con-4-habitaciones-en-cap-cana",
        "villa-golf-en-las-iguanas-cap-cana-4-habitaciones",
        "samana-villas-nuevo-complejo-con-villas-y-apartamentos-desde-us150000",
        "portillo-las-terrenas-apartamentos-con-vista-al-mar",
        "cap-cana-moderno-y-lujoso-desarrollo-apartamentos-de-12-y-3-habitaciones",
        "cap-cana-nuevo-desarrollo-con-con-precios-de-lanzamiento-1-y-2-habs",
        "punta-cana-acces-to-private-beach-2-bedroom-apartments",
        "palm-view-coral-golf-resort-and-residences",
        "kasa-living-residencias-en-downtown-punta-cana",
        "villa-de-2-3-habitaciones-y-2-3-banos-en-punta-cana",
        "momentum-residences-descubre-tu-paraiso-caribeno-en-vista-cana",
        "new-punta-cana-tropical-houses-townhouses-at-gated-community-with-golf-course",
        "14-roi-condohotel-en-punta-cana",
        "comunidad-cerrada-con-amenidades-de-lujo-villas-apartamentos-y-town-houses",
        "exquisitos-apartamentos-de-2-habitaciones-tu-oasis-en-villas-bavaro",
        "apartamentos-espaciosos-de-75m2-tu-oasis-de-vida-moderna-en-bavaro",
        "vivienda-de-lujo-en-playa-nueva-romana-tu-refugio-exclusivo",
        "exclusivo-3-habitaciones-villas-en-playa-nueva-romana-con-confotur",
        "nuevo-complejo-de-villas-de-2-y-3-habitaciones-en-bavaro",
        "punta-cana-2-habs-apartamento-listo-a-500-mts-de-la-playa",
        "exclusive-apartments-at-bayahibe-600-mt-from-the-beach",
        "punta-cana-los-corales-1-2-habs-caminando-a-la-playa",
        "8-min-caminando-a-la-playa-2-habitaciones-y-2-banos",
        "experiencia-de-vida-de-lujo-en-punta-cana-villas-con-confotur",
        "unidades-de-lujo-junto-al-mar-en-bayahibe-1-y-2-habitaciones",
        "exclusivos-apartamentos-de-1-y-2-habitaciones-en-brisas-de-punta-cana",
        "vivienda-de-lujo-moderna-en-vista-cana3-4-habitaciones-villas-disponibles-ahora",
        "luxury-oceanfront-living-in-cabarete-stunning-views",
        "torre-en-la-esmeralda-elegancia-e-innovacion-en-santiago",
        "vistas-exclusivas-en-thomen-apartamentos-de-lujo-y-seguridad",
        "vive-la-modernidad-en-la-codiciada-thomen",
        "listo-apartamento-de-3-habitaciones-con-25-banos-en-santiago",
        "ocean-view-apartments-at-the-marina-cap-cana",
        "just-launched-minimalist-villa-at-vista-cana-punta-cana",
        "nuevas-villas-de-3-habs-en-downtown-punta-cana",
        "golf-view-furnished-apartments-at-cabeza-de-toro",
        "solares-en-venta-en-downtown-punta-cana-confotur-la-reserva",
        "cap-cana-nuevo-desarrollo-a-precios-de-oportunidad",
        "modernos-apartamentos-en-bavaro-cerca-de-todo",
        "descubre-el-confort-elevado-a-nuevas-alturas",
        "alturas-de-lujo-6-torres-emblematicas-en-el-epicentro-urbano",
        "riviera-bay-cana-bay-punta-cana",
        "jardines-iii-bavaro-punta-cana",
        "townhouses-portofino-las-terrenas",
        "descubre-esta-excelente-oportunidad-de-inversion-en-el-centro-de-santiago",
        "nuevo-desarrollo-en-cap-cana-7-min-a-playa-juanillo",
        "modernas-villas-akana-ciudad-las-canas",
        "villas-de-3-habitaciones-en-comunidad-cerrada-vista-cana",
        "nuevo-desarrollo-de-apartamentos-en-cocotal-golf-country-club",
        "nuevas-villas-unicas-en-punta-cana-en-comunidad-privada",
        "bayahibe-caminando-a-la-playa-paraiso-tropical-con-apartamentos-de-lujo",
        "exclusivos-apartamentos-de-3-habitaciones-a-solo-8-minutos-del-centro-de-santiago",
        "punta-cana-10-min-a-la-playa-luxury-2-habs-apartamentos-en-los-corales-punta-cana",
        "disfruta-de-la-comodidad-en-cada-rincon-villas-duplex-en-cocotal-golf-country-club",
        "exclusivo-complejo-de-villas-duplex-de-3-habitaciones-en-brisas-de-punta-cana",
        "nuevo-punta-cana-luxury-condos-en-downtown",
        "desarrollo-de-lujo-en-downtown-punta-cana-con-apartmentos-de-1-y-2-habitaciones",
        "apartamentos-a-precios-de-oportunidad-downtown-punta-cana",
        "villa-exquisita-de-4-habitaciones-en-punta-cana-village",
        "villa-de-4-habitaciones-en-el-village",
        "alcanza-la-cima-del-estilo-de-vida-en-exclusivo-proyecto-de-apartamentos-en-santiago",
        "villas-boho-chic-en-downtown-punta-cana",
        "tropical-villas-de-3-habitaciones-a-2-minutos-de-playa-macao",
        "casa-en-punta-cana-village-espacios-amplios-y-lista-para-vivir",
        "residencia-en-punta-cana-village-lujo-comodidad-y-listo-para-mudarse",
        "villa-laguna-24-tranquilidad-lujo-y-diseno-exquisito",
        "villa-107-lujo-y-elegancia-entrega-abril-2024-vista-al-campo-de-golf",
        "villa-106-en-cap-cana-lujo-privacidad-y-proximidad-a-los-mejores-destinos",
        "exquisita-villa-de-lujo-en-cap-cana-piscina-privada-jacuzzi-y-terrazas-villa-105",
        "apartamentos-contemporaneos-en-punta-cana-2-y-3-habs-precios-de-oportunidad",
        "apartamentos-de-1-y-2-habitaciones-en-downtown-punta-cana",
        "cap-cana-nuevo-desarrollo-aptos-de-1-a-3-habitaciones-caminando-a-la-playa",
        "locales-comerciales-en-nueva-plaza-contemporanea-en-el-corazon-de-downtown-punta-cana",
        "apartamentos-en-punta-cana-caminando-a-la-playa",
        "torre-residencial-de-lujo-en-naco-santo-domingo",
        "comodidad-exclusiva-en-santo-domingo-norte-con-bono-de-vivienda",
        "discover-comfort-in-every-corner-of-the-exclusive-residential-complex-in-servalles",
        "experience-the-comfort-in-every-space-discover-the-new-complex-of-duplex-villas-in-vista-cana",
        "1st-class-finishes-villas-with-3-bedrooms-and-open-layout",
        "caribbean-colonial-1-2-br-apartments-in-punta-cana",
        "tax-free-2-and-3-bedrooms-apartments-in-punta-cana",
        "experience-comfort-and-modernity-in-every-space-discover-the-new-complex-in-pueblo-bavaro",
        "live-in-comfort-in-every-space-discover-the-new-complex-in-vista-cana-with-confotur",
        "discover-the-exclusivity-and-comfort-of-our-new-complex-in-brisas-de-punta-cana",
        "experience-comfort-in-every-space-discover-the-new-complex-of-three-bedroom-villas-in-punta-cana",
        "modern-apartments-villas-close-to-everything",
        "confortable-and-spacious1-bedroom-2-bathrooms-apartment-in-a-gated-complex-with-a-pool",
        "spacious-and-comfortable-1-bedroom-2-bathroom-apartment-in-a-gated-complex-with-confotur",
        "exclusive-3-bedroom-villa-complex-with-pool-in-whitesands",
        "exclusive-complex-of-11-townhouses-with-a-pool-and-terrace-in-bavaro",
        "complejo-cerrado-con-villas-y-apartamentos-con-vista-a-la-playa-de-vista-cana",
        "exclusivo-desarrollo-de-apartamentos-cerrado-de-1-y-2-habitaciones-en-vista-cana",
        "3-bedroom-townhouses-with-patio-at-vista-cana",
        "private-gated-community-of-50-detached-villas-fully-equipped-kitchen",
        "3-min-caminando-a-playa-dominicus-nuevos-apartamentos-1-2-habitaciones",
        "luxury-apartments-with-rooftops-social-areas-near-punta-cana",
        "3-bed-duplex-en-vista-cana",
        "nuevo-desarrollo-de-apartamentos-en-arroyo-hondo-santo-domingo",
        "super-precios-apartamentos-de-2-habitaciones-en-bayahibe",
        "hermosas-villas-en-playa-macao",
        "luxury-apartments-in-cap-cana-sea-view",
        "4-min-to-the-beach-beautiful-2-bedrooms-apartment-in-las-terrenas-samana",
        "listo-apartamento-en-los-corales-10-min-de-la-playa",
        "stunning-luxury-3-bedrooms-villas-in-vista-cana",
        "modern-villas-at-downtown-punta-cana",
        "2-3-bedrooms-townhouses-in-los-corales-punta-cana",
        "luxury-residential-tower-in-serralles-santo-domingo",
        "investment-apartments-in-santo-domingo-strategic-location",
        "1-2-rooms-apartments-in-vista-cana-invest-safely",
        "stunning-4-bedrooms-villa-in-punta-cana-resorts-club",
        "luxury-and-tropical-5-rooms-villa-in-punta-cana-resorts",
        "reduced-price-4-bedroom-villa-at-punta-cana-village",
        "4-bedrooms-villa-in-punta-cana-villa",
        "stunning-apartments-in-cap-cana",
        "luxury-apartments-in-vista-cana-affordable-prices",
        "luxury-gated-community-with-villas-and-condos-in-vista-cana",
        "tropical-design-apartments-in-vista-cana",
        "exclusive-private-villa-complex",
        "invierte-en-esta-torre-residencial-en-el-corazon-de-piantini",
        "opportunity-prices-1-to-2-rooms-apartments-in-punta-cana",
        "luxury-condos-with-artificial-beach-confotur-and-appliances-included",
        "3-rooms-villas-with-amazing-prices",
        "amplios-y-exclusivos-apartamentos-en-los-cacigazcos",
        "apartments-in-cap-cana-golf-course-views",
        "luxury-villas-in-vista-cana",
        "beautiful-apartments-in-the-marina-cap-cana",
        "new-apartments-in-cocotal-golf-country-club",
        "villas-and-apartments-walking-distance-to-the-beach",
        "apartments-and-villas-walking-distance-to-portillo-beach-las-terrenas",
        "punta-cana-gated-community-with-opportunity-prices",
        "apartments-walking-distance-to-the-beach-at-los-corales",
        "apartamentos-en-venta-en-primera-linea-de-playa-en-las-terrenas-samana",
        "apartamentos-extraordinarios-completamente-amueblados-en-punta-cana",
        "apartamentos-con-vista-a-campo-de-golf",
    ]
    return [f"{BASE_URL}/propiedad/{s}" for s in slugs]


# ============================================================
# EXTRAER DATOS DE CADA PROPIEDAD
# ============================================================
def scrape_property(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  Error {r.status_code}: {url}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        slug = url.rstrip("/").split("/")[-1]

        # Título
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "").replace(" - Eskala Real Estate", "").strip()
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # Descripción
        description = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            description = og_desc.get("content", "").strip()

        # Imágenes — prioridad a og:image, luego todas las de CloudFront
        images = []
        og_img = soup.find("meta", property="og:image")
        if og_img:
            img_url = og_img.get("content", "")
            if img_url:
                images.append(img_url)
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "cloudfront.net" in src and src not in images:
                images.append(src)

        # Precio
        price = 0
        price_matches = re.findall(r'US\$\s*([\d,]+)', soup.get_text())
        if price_matches:
            try:
                price = int(price_matches[0].replace(",", ""))
            except:
                pass

        # Tipo de operación
        advert_type = "Sale"
        url_lower = url.lower()
        if any(w in url_lower for w in ["alquiler", "renta", "rent"]):
            advert_type = "Rent"

        # Tipo de propiedad
        title_lower = title.lower()
        sub_type = "Apartment"
        if "villa" in url_lower or "villa" in title_lower:
            sub_type = "Villa"
        elif any(w in url_lower for w in ["casa", "house", "residencia"]):
            sub_type = "House"
        elif any(w in url_lower for w in ["solar", "terreno", "plot"]):
            sub_type = "PlotOfLand"
        elif any(w in url_lower for w in ["local", "comercial", "office"]):
            sub_type = "Commercial"
        elif any(w in url_lower for w in ["townhouse", "duplex"]):
            sub_type = "House"

        # Ciudad
        city = "Santo Domingo"
        city_map = {
            "punta-cana": "Punta Cana", "bavaro": "Bávaro", "cap-cana": "Cap Cana",
            "bayahibe": "Bayahibe", "santiago": "Santiago", "la-romana": "La Romana",
            "las-terrenas": "Las Terrenas", "samana": "Samaná", "jarabacoa": "Jarabacoa",
            "puerto-plata": "Puerto Plata", "cabarete": "Cabarete", "sosua": "Sosúa",
            "juan-dolio": "Juan Dolio", "macao": "Macao", "vista-cana": "Punta Cana",
            "downtown": "Punta Cana", "uvero-alto": "Punta Cana",
        }
        for key, val in city_map.items():
            if key in url_lower:
                city = val
                break

        # Habitaciones
        bedrooms = 0
        bed_match = re.search(r'(\d+)\s*hab', title_lower)
        if bed_match:
            bedrooms = int(bed_match.group(1))
        else:
            for n in ["7", "6", "5", "4", "3", "2", "1"]:
                if f"{n} bedroom" in title_lower:
                    bedrooms = int(n)
                    break

        return {
            "id": slug,
            "url": url,
            "title": title,
            "description": description,
            "images": images,
            "price": price,
            "currency": "USD",
            "advert_type": advert_type,
            "sub_type": sub_type,
            "city": city,
            "country": "DO",
            "bedrooms": bedrooms,
        }

    except Exception as e:
        print(f"  Excepción en {url}: {e}")
        return None


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
        ET.SubElement(advert, "AdvertId").text = prop["id"][:20]
        ET.SubElement(advert, "OriginalUrl").text = prop["url"]
        ET.SubElement(advert, "AdvertType").text = prop["advert_type"]
        ET.SubElement(advert, "SubType").text = prop["sub_type"]
        ET.SubElement(advert, "Status").text = "Active"
        ET.SubElement(advert, "PublicationDate").text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        if prop["bedrooms"] > 0:
            ET.SubElement(advert, "Bedrooms").text = str(prop["bedrooms"])

        descs = ET.SubElement(advert, "Descriptions")
        desc_el = ET.SubElement(descs, "Description")
        desc_el.set("Language", "es")
        desc_el.text = prop["description"]

        titles_el = ET.SubElement(advert, "Titles")
        title_el = ET.SubElement(titles_el, "Title")
        title_el.set("Language", "es")
        title_el.text = prop["title"]

        ET.SubElement(advert, "Price").text = str(prop["price"]) if prop["price"] > 0 else "0"
        ET.SubElement(advert, "PriceCurrency").text = prop["currency"]
        ET.SubElement(advert, "ShowPrice").text = "1" if prop["price"] > 0 else "0"

        ET.SubElement(advert, "Country").text = "DO"
        ET.SubElement(advert, "City").text = prop["city"]
        ET.SubElement(advert, "PostalCode").text = "00000"

        if prop["images"]:
            photos = ET.SubElement(advert, "Photos")
            for img_url in prop["images"][:15]:
                ET.SubElement(photos, "Photo").text = img_url

    xml_str = ET.tostring(root, encoding="unicode")
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  ", encoding="UTF-8").decode("UTF-8")


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"[{datetime.now()}] Iniciando generación de feed Properstar...")

    urls = get_property_urls()

    properties = []
    for i, url in enumerate(urls):
        print(f"  [{i+1}/{len(urls)}] {url}")
        prop = scrape_property(url)
        if prop:
            properties.append(prop)
        time.sleep(0.5)

    print(f"\nPropiedades procesadas: {len(properties)}")

    xml_content = generate_xml(properties)

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"Feed generado exitosamente: feed.xml")
    print(f"URL pública: https://eskalarealestate.github.io/eskala-feed/feed.xml")


if __name__ == "__main__":
    main()

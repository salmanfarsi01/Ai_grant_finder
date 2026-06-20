import json
import re
from typing import List, Dict, Any, Tuple

from pinecone import Pinecone
from openai import OpenAI
from tiktoken import get_encoding
from deep_translator import GoogleTranslator
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import os


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("API keys are missing! Please check your .env file.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)


DEFAULT_INDEX_NAME = "scholarships-index-latest"
INDEX_NAME = DEFAULT_INDEX_NAME
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
DEFAULT_TOP_K = 200
MAX_CANDIDATES_FOR_LLM = 200
MIN_RESULTS = 10

enc = get_encoding("cl100k_base")

_BOX_CLEAN = re.compile(
    r'[\u25A0\u25AA\u25AB\u25FB\u25FC\u25FD\u25FE' 
    r'\u2500-\u257F' 
    r'\u2580-\u259F'  
    r'\u2600-\u26FF'  
    r'\u2B1B\u2B1C\u2B50\u2B55'  
    r'\u00AD\u200B\u200C\u200D\uFEFF'  
    r'\u2028\u2029'  
    r'\u061C\u200E\u200F'  
    r'\x00-\x08\x0B\x0C\x0E-\x1F' 
    r'\x7F-\x9F'  
    r'\u0300-\u036F]'  
)


_ESCAPE_SEQ = re.compile(r'_x[0-9A-Fa-f]{4}_')

_BOX_REPLACE = {
    '\u2018': "'", '\u2019': "'",
    '\u201C': '"', '\u201D': '"',
    '\u2013': '-', '\u2014': '-',
    '\u2026': '...', '\u00AB': '"',
    '\u00BB': '"', '\u00A0': ' ',
    '\u2022': '-',
}

def _clean_raw(text):
    if not isinstance(text, str):
        return text
    
   
    text = _ESCAPE_SEQ.sub('', text)
    
   
    text = _BOX_CLEAN.sub('', text)
    
    
    for char, rep in _BOX_REPLACE.items():
        text = text.replace(char, rep)
    
    
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def get_active_index():
    """Get the active Pinecone index, with fallback to hardcoded default"""
    global INDEX_NAME
    try:
        from django.conf import settings
        if settings.SITE_CONFIG:
            INDEX_NAME = settings.SITE_CONFIG.get_active_dataset_index_name()
    except Exception as e:
        print(f"Warning: Could not load INDEX_NAME from SiteConfig, using default: {e}")
        INDEX_NAME = DEFAULT_INDEX_NAME
    return pc.Index(INDEX_NAME)

index = pc.Index(INDEX_NAME)
MUNICIPALITY_NAME_MAP = {

    "ale": "Ale",
    "alingsas": "Alingsås",
    "alingsås": "Alingsås",
    "alvesta": "Alvesta",
    "aneby": "Aneby",
    "arboga": "Arboga",
    "arjeplog": "Arjeplog",
    "arvidsjaur": "Arvidsjaur",
    "arvika": "Arvika",
    "askersund": "Askersund",
    "avesta": "Avesta",
    "bengtsfors": "Bengtsfors",
    "berg": "Berg",
    "bjurholm": "Bjurholm",
    "bjuv": "Bjuv",
    "boden": "Boden",
    "bollebygd": "Bollebygd",
    "bollnas": "Bollnäs",
    "bollnäs": "Bollnäs",
    "borgholm": "Borgholm",
    "borlange": "Borlänge",
    "borlänge": "Borlänge",
    "boras": "Borås",
    "borås": "Borås",
    "botkyrka": "Botkyrka",
    "boxholm": "Boxholm",
    "bromolla": "Bromölla",
    "bromölla": "Bromölla",
    "bracke": "Bräcke",
    "bräcke": "Bräcke",
    "burlov": "Burlöv",
    "burlöv": "Burlöv",
    "bastad": "Båstad",
    "båstad": "Båstad",
    "dals-ed": "Dals-Ed",
    "danderyd": "Danderyd",
    "degerfors": "Degerfors",
    "dorotea": "Dorotea",
    "eda": "Eda",
    "ekero": "Ekerö",
    "ekerö": "Ekerö",
    "eksjo": "Eksjö",
    "eksjö": "Eksjö",
    "emmaboda": "Emmaboda",
    "enkoping": "Enköping",
    "enköping": "Enköping",
    "eskilstuna": "Eskilstuna",
    "eslov": "Eslöv",
    "eslöv": "Eslöv",
    "essunga": "Essunga",
    "fagersta": "Fagersta",
    "falkenberg": "Falkenberg",
    "falkoping": "Falköping",
    "falköping": "Falköping",
    "falun": "Falun",
    "filipstad": "Filipstad",
    "finspang": "Finspång",
    "finspång": "Finspång",
    "flen": "Flen",
    "forshaga": "Forshaga",
    "fargelanda": "Färgelanda",
    "färgelanda": "Färgelanda",
    "gagnef": "Gagnef",
    "gislaved": "Gislaved",
    "gnesta": "Gnesta",
    "gnosjo": "Gnosjö",
    "gnosjö": "Gnosjö",
    "gotland": "Gotland",
    "grums": "Grums",
    "grastorp": "Grästorp",
    "grästorp": "Grästorp",
    "gullspang": "Gullspång",
    "gullspång": "Gullspång",
    "gallivare": "Gällivare",
    "gällivare": "Gällivare",
    "gavle": "Gävle",
    "gävle": "Gävle",
    "gotene": "Götene",
    "götene": "Götene",
    "gothenburg": "Göteborg",
    "goteborg": "Göteborg",
    "göteborg": "Göteborg",
    #"habo": "Habo",
    "hagfors": "Hagfors",
    "hallsberg": "Hallsberg",
    "hallstahammar": "Hallstahammar",
    "halmstad": "Halmstad",
    "hammaro": "Hammarö",
    "hammarö": "Hammarö",
    "haninge": "Haninge",
    "haparanda": "Haparanda",
    "heby": "Heby",
    "hedemora": "Hedemora",
    "helsingborg": "Helsingborg",
    "herrljunga": "Herrljunga",
    "hjo": "Hjo",
    "hofors": "Hofors",
    "huddinge": "Huddinge",
    "hudiksvall": "Hudiksvall",
    "hultsfred": "Hultsfred",
    "hylte": "Hylte",
    "habo": "Habo", 
    "håbo": "Håbo", 
    "hallefors": "Hällefors",
    "hällefors": "Hällefors",
    "harjedalen": "Härjedalen",
    "härjedalen": "Härjedalen",
    "harnosand": "Härnösand",
    "härnösand": "Härnösand",
    "harryda": "Härryda",
    "härryda": "Härryda",
    "hassleholm": "Hässleholm",
    "hässleholm": "Hässleholm",
    "hoganas": "Höganäs",
    "höganäs": "Höganäs",
    "hogsby": "Högsby",
    "högsby": "Högsby",
    "horby": "Hörby",
    "hörby": "Hörby",
    "hoor": "Höör",
    "höör": "Höör",
    "jokkmokk": "Jokkmokk",
    "jarfalla": "Järfälla",
    "järfälla": "Järfälla",
    "jonkoping": "Jönköping",
    "jönköping": "Jönköping",
    "kalix": "Kalix",
    "kalmar": "Kalmar",
    "karlsborg": "Karlsborg",
    "karlshamn": "Karlshamn",
    "karlskoga": "Karlskoga",
    "karlskrona": "Karlskrona",
    "karlstad": "Karlstad",
    "katrineholm": "Katrineholm",
    "kil": "Kil",
    "kinda": "Kinda",
    "kiruna": "Kiruna",
    "klippan": "Klippan",
    "knivsta": "Knivsta",
    "kramfors": "Kramfors",
    "kristianstad": "Kristianstad",
    "kristinehamn": "Kristinehamn",
    "krokom": "Krokom",
    "kumla": "Kumla",
    "kungsbacka": "Kungsbacka",
    "kungsor": "Kungsör",
    "kungsör": "Kungsör",
    "kungalv": "Kungälv",
    "kungälv": "Kungälv",
    "kavlinge": "Kävlinge",
    "kävlinge": "Kävlinge",
    "koping": "Köping",
    "köping": "Köping",
    "laholm": "Laholm",
    "laxa": "Laxå",
    "laxå": "Laxå",
    "lekeberg": "Lekeberg",
    "leksand": "Leksand",
    "lerum": "Lerum",
    "lessebo": "Lessebo",
    "lidingo": "Lidingö",
    "lidingö": "Lidingö",
    "lidkoping": "Lidköping",
    "lidköping": "Lidköping",
    "lilla edet": "Lilla Edet",
    "lindesberg": "Lindesberg",
    "linkoping": "Linköping",
    "linköping": "Linköping",
    "ljungby": "Ljungby",
    "ljusdal": "Ljusdal",
    "ljusnarsberg": "Ljusnarsberg",
    "lomma": "Lomma",
    "ludvika": "Ludvika",
    "lulea": "Luleå",
    "luleå": "Luleå",
    "lund": "Lund",
    "lycksele": "Lycksele",
    "lysekil": "Lysekil",
    "malmo": "Malmö",
    "malmö": "Malmö",
    "malung-salen": "Malung-Sälen",
    "malung-sälen": "Malung-Sälen",
    "mala": "Malå",
    "malå": "Malå",
    "mariestad": "Mariestad",
    "mark": "Mark",
    "markaryd": "Markaryd",
    "mellerud": "Mellerud",
    "mjolby": "Mjölby",
    "mjölby": "Mjölby",
    "mora": "Mora",
    "motala": "Motala",
    "munkedal": "Munkedal",
    "munkfors": "Munkfors",
    "molndal": "Mölndal",
    "mölndal": "Mölndal",
    "monsteras": "Mönsterås",
    "mönsterås": "Mönsterås",
    "morbylanga": "Mörbylånga",
    "mörbylånga": "Mörbylånga",
    "nacka": "Nacka",
    "nora": "Nora",
    "norberg": "Norberg",
    "nordanstig": "Nordanstig",
    "nordmaling": "Nordmaling",
    "norrkoping": "Norrköping",
    "norrköping": "Norrköping",
    "norrtalje": "Norrtälje",
    "norrtälje": "Norrtälje",
    "norsjo": "Norsjö",
    "norsjö": "Norsjö",
    "nybro": "Nybro",
    "nykvarn": "Nykvarn",
    "nykoping": "Nyköping",
    "nyköping": "Nyköping",
    "nynashamn": "Nynäshamn",
    "nynäshamn": "Nynäshamn",
    "nassjo": "Nässjö",
    "nässjö": "Nässjö",
    "ockelbo": "Ockelbo",
    "olofstrom": "Olofström",
    "olofström": "Olofström",
    "orsa": "Orsa",
    "orust": "Orust",
    "osby": "Osby",
    "oskarshamn": "Oskarshamn",
    "ovanaker": "Ovanåker",
    "ovanåker": "Ovanåker",
    "oxelosund": "Oxelösund",
    "oxelösund": "Oxelösund",
    "pajala": "Pajala",
    "partille": "Partille",
    "perstorp": "Perstorp",
    "pitea": "Piteå",
    "piteå": "Piteå",
    "ragunda": "Ragunda",
    "robertsfors": "Robertsfors",
    "ronneby": "Ronneby",
    "rattvik": "Rättvik",
    "rättvik": "Rättvik",
    "sala": "Sala",
    "salem": "Salem",
    "sandviken": "Sandviken",
    "sigtuna": "Sigtuna",
    "simrishamn": "Simrishamn",
    "sjobo": "Sjöbo",
    "sjöbo": "Sjöbo",
    "skara": "Skara",
    "skelleftea": "Skellefteå",
    "skellefteå": "Skellefteå",
    "skinnskatteberg": "Skinnskatteberg",
    "skurup": "Skurup",
    "skovde": "Skövde",
    "skövde": "Skövde",
    "smedjebacken": "Smedjebacken",
    "solleftea": "Sollefteå",
    "sollefteå": "Sollefteå",
    "sollentuna": "Sollentuna",
    "solna": "Solna",
    "sorsele": "Sorsele",
    "sotenas": "Sotenäs",
    "sotenäs": "Sotenäs",
    "staffanstorp": "Staffanstorp",
    "stenungsund": "Stenungsund",
    "stockholm": "Stockholm",
    "storfors": "Storfors",
    "storuman": "Storuman",
    "strangnas": "Strängnäs",
    "strängnäs": "Strängnäs",
    "stromstad": "Strömstad",
    "strömstad": "Strömstad",
    "stromsund": "Strömsund",
    "strömsund": "Strömsund",
    "sundbyberg": "Sundbyberg",
    "sundsvall": "Sundsvall",
    "sunne": "Sunne",
    "surahammar": "Surahammar",
    "svalov": "Svalöv",
    "svalöv": "Svalöv",
    "svedala": "Svedala",
    "svenljunga": "Svenljunga",
    "saffle": "Säffle",
    "säffle": "Säffle",
    "sater": "Säter",
    "säter": "Säter",
    "savsjo": "Sävsjö",
    "sävsjö": "Sävsjö",
    "solvesborg": "Sölvesborg",
    "sölvesborg": "Sölvesborg",
    "tanum": "Tanum",
    "tibro": "Tibro",
    "tidaholm": "Tidaholm",
    "tierp": "Tierp",
    "timra": "Timrå",
    "timrå": "Timrå",
    "tingsryd": "Tingsryd",
    "tjorn": "Tjörn",
    "tjörn": "Tjörn",
    "tomelilla": "Tomelilla",
    "torsby": "Torsby",
    "torsas": "Torsås",
    "torsås": "Torsås",
    "tranemo": "Tranemo",
    "tranas": "Tranås",
    "tranås": "Tranås",
    "trelleborg": "Trelleborg",
    "trollhattan": "Trollhättan",
    "trollhättan": "Trollhättan",
    "trosa": "Trosa",
    "tyreso": "Tyresö",
    "tyresö": "Tyresö",
    "taby": "Täby",
    "täby": "Täby",
    "toreboda": "Töreboda",
    "töreboda": "Töreboda",
    "uddevalla": "Uddevalla",
    "ulricehamn": "Ulricehamn",
    "umea": "Umeå",
    "umeå": "Umeå",
    "upplands-bro": "Upplands-Bro",
    "upplands vasby": "Upplands Väsby",
    "upplands väsby": "Upplands Väsby",
    "uppsala": "Uppsala",
    "uppvidinge": "Uppvidinge",
    "vadstena": "Vadstena",
    "vaggeryd": "Vaggeryd",
    "valdemarsvik": "Valdemarsvik",
    "vallentuna": "Vallentuna",
    "vansbro": "Vansbro",
    "vara": "Vara",
    "varberg": "Varberg",
    "vaxholm": "Vaxholm",
    "vellinge": "Vellinge",
    "vetlanda": "Vetlanda",
    "vilhelmina": "Vilhelmina",
    "vimmerby": "Vimmerby",
    "vindeln": "Vindeln",
    "vingaker": "Vingåker",
    "vingåker": "Vingåker",
    "vanersborg": "Vänersborg",
    "vänersborg": "Vänersborg",
    "vannas": "Vännäs",
    "vännäs": "Vännäs",
    "vasteras": "Västerås",
    "västerås": "Västerås",
    "vaxjo": "Växjö",
    "växjö": "Växjö",
    "vargarda": "Vårgårda",
    "vårgårda": "Vårgårda",
    "ydre": "Ydre",
    "ystad": "Ystad",
    "amal": "Åmål",
    "åmål": "Åmål",
    "ange": "Ånge",
    "ånge": "Ånge",
    "are": "Åre",
    "åre": "Åre",
    "arjang": "Årjäng",
    "årjäng": "Årjäng",
    "asele": "Åsele",
    "åsele": "Åsele",
    "astorp": "Åstorp",
    "åstorp": "Åstorp",
    "atvidaberg": "Åtvidaberg",
    "åtvidaberg": "Åtvidaberg",
    "almhult": "Älmhult",
    "älmhult": "Älmhult",
    "alvdalen": "Älvdalen",
    "älvdalen": "Älvdalen",
    "alvkarleby": "Älvkarleby",
    "älvkarleby": "Älvkarleby",
    "alvsbyn": "Älvsbyn",
    "älvsbyn": "Älvsbyn",
    "angelholm": "Ängelholm",
    "ängelholm": "Ängelholm",
    "ockero": "Öckerö",
    "öckerö": "Öckerö",
    "odeshog": "Ödeshög",
    "ödeshög": "Ödeshög",
    "orebro": "Örebro",
    "örebro": "Örebro",
    "orkelljunga": "Örkelljunga",
    "örkelljunga": "Örkelljunga",
    "ornskoldsvik": "Örnsköldsvik",
    "örnsköldsvik": "Örnsköldsvik",
    "ostersund": "Östersund",
    "östersund": "Östersund",
    "osteraker": "Österåker",
    "österåker": "Österåker",
    "osthammar": "Östhammar",
    "östhammar": "Östhammar",
    "ostra goinge": "Östra Göinge",
    "östra göinge": "Östra Göinge",
    "landskrona": "Landskrona", 
    "mullsjo": "Mullsjö", 
    "mullsjö": "Mullsjö", 
    "varmdo": "Värmdö", 
    "värmdö": "Värmdö", 
    "varnamo": "Värnamo", 
    "värnamo": "Värnamo", 
    "vastervik": "Västervik", 
    "västervik": "Västervik", 
    "overkalix": "Överkalix", 
    "överkalix": "Överkalix", 
    "overtornea": "Övertorneå", 
    "övertorneå": "Övertorneå", 
    "sodertalje": "Södertälje", 
    "södertälje": "Södertälje", 
    "soderkoping": "Söderköping", 
    "söderköping": "Söderköping", 
    "soderhamn": "Söderhamn", 
    "söderhamn": "Söderhamn",
}
FIELD_MAP_SV = {
    "Name": "Namn",
    "Purpose": "Ändamål",
    "Study Level": "Utbildningsnivå",
    "Municipality": "Kommun",
    "Category": "Kategori",
    "Email": "Epost",
    "Website": "Websida",
    "Phone": "Telefon",
    "Assets": "Tillgångar",
    "Main Address": "Huvudadress",
    "Postal Code": "Postnr",
    "City": "Stad",
    "County": "Län",
    "Sport": "Sport",
}


NAME_INSTITUTION_TERMS = [
    "professur", "gästprofessur", "professuren",
    "lektorat", "docentur", "docenttjänst",
]


DIRECT_STUDENT_BENEFIT_OVERRIDES = [
    "stipendium till studerande", "stipendier till studerande",
    "stipendium till studenter", "stipendier till studenter",
    "bidrag till studerande", "bidrag till studenter",
    "till förmån för studerande", "till förmån för studenter",
    "studiestipendium", "studiestipendier",
    "studentstipendium", "studentstipendier",
]

BUSINESS_TERMS = [
    "business", "economics", "finance", "financial", "accounting", "banking",
    "management", "commerce", "entrepreneurship", "företagsekonomi", "ekonomi",
    "finans", "redovisning", "handel", "business administration", "marknadsföring",
    "marketing", "handelshögskolan", "ekonomisk", "ekonomiska",
    "nationalekonomi", "affärsinriktade studier", "affärsinriktad",
]

LAW_TERMS = [
    "law", "legal", "juridik", "juridisk", "affärsjuridik", "business law",
    "commercial law", "jurisprudence", "rättsvetenskap", "jurist", "juridiska",
    "folkrätt", "eg-rätt", "sjörätt", "transporträtt",
    "företagsjuridik", "företagsjuridiska",
    "rättsvetenskaplig", "rättsvetenskapliga",
    "affärsjuridiska",
    "sjörättens", "sjö- och transport",
    "transporträttens",
    "straffrätt", "civilrätt", "processrätt",
    "förvaltningsrätt", "miljörätt", "immaterialrätt",
    "arbetsrätt", "skatterätt", "familjerätt",
    "avtalsrätt", "offentlig rätt", "internationell rätt",
    "rättsinformation", "rättskällor",
    "juridikstuderande", "juriststuderande",
    "juridikstudent", "juriststudent",
    "juridiska fakultet", "juridiska fakulteten",
    "juridisk utbildning", "juristutbildning",
    "law student", "law faculty",
    "handelsrätt", "handelsrättens", "handelsrättslig",
    "köprätt", "kontraktsrätt",
    "bolags rätt", "bolagsrätt", "associationsrätt",
]

TECHNOLOGY_TERMS = [
    "technology", "teknik", "engineering", "ingenjör", "computer science",
    "datavetenskap", "it", "software", "programming", "programmering",
    "data science", "ai", "artificial intelligence", "machine learning",
    "cybersecurity", "nätverk", "elektronik", "elektroteknik",
    "civilingenjör", "teknisk", "tekniska",
]

NON_LAW_DOMAIN_TERMS = [
    "medicin", "medicine", "medical", "läkemedel", "pharmaceutical", "farmaci",
    "pharmacy", "hälsa", "health", "sjukvård", "healthcare", "nursing",
    "omvårdnad", "tandvård", "dentistry", "dental", "kirurgi", "surgery",
    "klinisk", "clinical", "biomedicin", "biomedical", "veterinär", "veterinary",
    "musik", "music", "musical", "konstnärlig", "artistic", "konst", "art",
    "teater", "theatre", "theater", "dans", "dance", "opera", "orkester",
    "biologi", "biology", "kemi", "chemistry", "fysik", "physics",
    "geologi", "geology", "astronomi", "astronomy", "botanik", "botany",
    "zoologi", "zoology", "ekologi", "ecology",
    "jordbruk", "agriculture", "lantbruk", "farming", "skogsbruk", "forestry",
    "karolinska", "karolinska institutet", "karolinska institutets",
    "medicinsk", "medicinska", "medicinare", "medicinstuderande",
    "sjöbefäl", "sjöfart", "sjöfartsutbildning", "nautisk", "nautiska",
    "sjöbefälsskola", "sjöbefälsskolans",
    "naturvetenskap", "naturvetenskaplig", "naturvetenskapliga",
    "matematik", "mathematics", "matematisk",
    "ingenjörsvetenskap", "teknikvetenskap",
    "naturbruk", "naturbruksgymnasiet",
    "drivhuset", "inkubator", "incubator",
]

NON_BUSINESS_DOMAIN_TERMS = [
    "medicin", "medicine", "medical", "läkemedel", "pharmaceutical",
    "sjukvård", "healthcare", "nursing", "tandvård", "dentistry",
    "kirurgi", "surgery", "klinisk", "clinical", "biomedicin",
    "musik", "music", "musical", "konstnärlig", "artistic",
    "teater", "theatre", "dans", "dance", "opera",
    "biologi", "biology", "kemi", "chemistry", "fysik", "physics",
    "jordbruk", "agriculture", "lantbruk", "skogsbruk", "forestry",
    "civilingenjör", "civilingenjörs",
    "master of science in engineering",
    "maskinteknik", "mechanical engineering",
    "datateknik", "computer engineering",
    "rymdteknik", "space technology",
    "energiteknik", "energy technology",
    "elektroteknik", "electrical engineering",
    "teknisk fysik", "engineering physics",
    "teknisk design", "technical design",
    "systemteknik", "systems engineering",
    "produktionsteknik", "production engineering",
    "materialteknik", "materials engineering",
    "byggteknik", "construction engineering",
    "fordonselektronik", "vehicle electronics",
    "programvaruteknik", "software engineering",
]

NON_TECH_DOMAIN_TERMS = [
    "medicin", "medicine", "musik", "music", "konstnärlig", "artistic",
    "jordbruk", "agriculture", "lantbruk", "teater", "theatre",
    "dans", "dance", "opera", "juridik", "law", "legal",
    
    "finansiell matematik", "financial mathematics",
    "industriell ekonomi", "industrial economics",
    "teknisk ekonomi",  
    "ekonomi och teknik",
]


STRICT_RESEARCH_ONLY_TERMS = [
    "doktorand", "doktorandnivå", "forskarutbildning", "forskarstuderande",
    "postdoktoral", "postdoc", "postdoctoral", "postdoktor", "gästprofessur",
    "efter avlagd doktorsexamen",
    "doctoral", "doctorate", "phd", "ph.d",
    "dissertation", "avhandling",
    "forskartjänst", "doktorsexamen", "licentiatexamen",
    "researcher position",
    "antagna till forskarutbildning",
    "studier efter avlagd doktorsexamen",
    "bedriver studier efter avlagd doktorsexamen",
]

ADVANCED_LEVEL_EXCLUSION_PHRASES = [
    "minst avancerad nivå",
    "avancerad nivå minst",
    "lägst avancerad nivå",
    "avancerad nivå eller högre",
]

DOCENT_EXCLUSIVE_TERMS = [
    "avlöning av en docent",
    "avlöning av docent",
    "till avlöning av en lärare (docent)",
    "docenttjänst",
    "docentur",
]

SOFT_RESEARCH_TERMS = [
    "research", "forskning", "research fund", "forskningsfond",
    "research foundation", "forskningsstiftelse", "scientific research",
    "vetenskaplig forskning", "vetenskapligt arbete",
    "vetenskapligt", "forskningsarbete"
]


INSTITUTION_SUPPORT_TERMS = [
    "guest professorship", "professorship", "professur", "professurer",
    "gästprofessur",
    "chair",
    "lektor", "lektorat",
    "avlöning av en lärare",
    "avlöning av en docent",
    "avlöning av docent",
    "avlöning av en professor",
]

INSTITUTION_COST_TERMS = [
    "seminariebibliotekets", "seminariebibliotek",
    "böcker till", "inköp av böcker",
    "bibliotekets",
    "institutionens drift",
    "underhåll av",
    "departmental costs",
    "faculty salary", "faculty salaries",
    "till en professur",
    "till professur",
    "medel skall användas till en professur",
    "till avlöning",
    "finansiera professuren",
    "helt eller delvis finansiera professuren",
    "inköp av böcker för seminariebiblioteket",
    "böcker för seminariebiblioteket",
    "inköp av böcker för seminarie",
]

ENTREPRENEURSHIP_SUPPORT_TERMS = [
    "drivhuset", "incubator", "inkubator", "startup support",
    "entrepreneurship support", "innovation hub", "innovation environment"
]

STRONG_DIRECT_SCHOLARSHIP_TERMS = [
    "stipendium", "stipend", "scholarship", "grant", "bidrag",
    "stipendiefond", "resestipendium", "studiestipendium",
    "stipendier", "studiebidrag"
]

BUSINESS_SCHOOL_STUDENT_TERMS = [
    "handelshögskolan", "school of business", "business school",
    "studentkår", "student union", "ekonomisk utbildning",
    "school of economics",
]

UNDERGRAD_TERMS = [
    "undergraduate", "bachelor", "bachelors", "candidate", "kandidat",
    "grundnivå", "grundutbildning", "kandidatexamen"
]



UNDERGRAD_INDICATOR_TERMS = [
    "grundutbildning", "grundnivå", "årskurs",
    "bachelor", "undergraduate",
    "kurser på grundnivå",
    "grundutbildningsnivå",
    "bachelor studies", "bachelor students",
]

DUAL_PURPOSE_PHRASES = [
    "forskning och utbildning",
    "utbildning och forskning",
    "undervisning och forskning",
    "forskning och undervisning",
    "vetenskaplig undervisning och forskning",
    "forskning, utbildning",
    "utbildning, forskning",
    "undervisning, forskning",
    "forskning och utbildning inom",
    "stödja forskning och utbildning",
    "främja forskning och utbildning",
    "forskning och undervisning vid",
    "stödja forskning och undervisning",
    "forskning och vetenskaplig undervisning",
    "vetenskaplig forskning och undervisning",
    "vetenskaplig forskning och vetenskaplig undervisning",
    "forskning och vetenskaplig undervisning- eller studieverksamhet",
    "undervisning- eller studieverksamhet",
    "forskning eller undervisning",
    "forskning eller utbildning",
    "utbildning eller forskning",
    "forskning, undervisning",
    "forskning samt utbildning",
    "forskning samt undervisning",
    "utbildning samt forskning",
    "forskning och utvecklingsverksamhet",
    "forskning och studieverksamhet",
    "forskning och vetenskaplig studieverksamhet",
    "vetenskaplig forskning och studieverksamhet",
    "främja forskning och undervisning",
    "stödja forskning och studieverksamhet",
    "främja och stödja forskning",
    "främja och stödja utbildning",
]

THESIS_STUDENT_TERMS = [
    "examensarbete", "examensarbeten",
    "kandidatuppsats", "kandidatuppsatser",
    "masteruppsats", "masteruppsatser",
    "magisteruppsats", "magisteruppsatser",
    "uppsats", "uppsatser",
    "slutarbete",
    "degree project",
    "bachelor thesis", "bachelor's thesis",
    "master thesis", "master's thesis",
    "uppsatstävling",
    "tävla med kandidat", "tävla med magister", "tävla med master",
]

FACULTY_WIDE_TERMS = [
    "studerande vid", "studenter vid", "elever vid",
    "studerande vid juridiska", "studenter vid juridiska",
    "studerande vid handelshögskolan", "studenter vid handelshögskolan",
    "studerande vid tekniska", "studenter vid tekniska",
    "studerande vid chalmers", "studenter vid chalmers",
    "studerande vid kth", "studenter vid kth",
    "studerande vid universitetet", "studenter vid universitetet",
    "studerande vid högskolan", "studenter vid högskolan",
    "inskrivna studerande", "inskrivna studenter",
    "studerande i ekonomi", "studerande i juridik",
    "studerande i teknik",
    "elever vid chalmers", "elever vid kth",
]

STRONG_STUDENT_TERMS = [
    "till studerande", "åt studerande", "för studerande",
    "till studenter", "åt studenter", "för studenter",
    "till elever", "åt elever", "för elever",
    "till student", "för student",
    "studerande vid", "studenter vid", "elever vid",
    "studerande som", "studenter som",
    "inskrivna studerande", "inskrivna studenter",
    "studiestipendium", "studiestipendier",
    "studentstipendium", "studentstipendier",
    "gymnasieelever",
    "for students", "to students",
    "bachelor students", "bachelor studies",
    "undergraduate students",
    "uppmuntra studenter", "stödja studenter",
    "stipendier till studenter", "stipendier till studerande",
    "stipendium till studenter",
    "kandidat", "kandidatuppsats", "kandidatuppsatser",
    "kandidatexamen", "kandidat-", "kandidatnivå",
    "bachelorstudent", "bachelorstudenter", "bachelor student",
    "grundnivå", "grundutbildning",
    "kurser på grundnivå",
    "årskurs 1", "årskurs 2", "årskurs 3", "årskurs",
    "masteruppsats", "masteruppsatser", "masterexamen",
    "magisteruppsats", "masternivå",
    "master's theses", "master's thesis",
    "bachelor's theses", "bachelor's thesis",
    "examensarbete", "examensarbeten",
    "uppsats", "uppsatser", "slutarbete",
    "juridiska fakulteten", "juridisk fakultet",
    "juridikstuderande", "juriststuderande",
    "studerande vid juridiska", "studenter vid juridiska",
    "handelshögskolan",
    "studerande vid handelshögskolan",
    "studenter vid handelshögskolan",
    "ekonomistuderande",
    "teknologer", "teknologer vid",
    "civilingenjörsstudenter", "ingenjörsstudenter",
    "studerande vid tekniska",
    "studenter vid chalmers", "studenter vid kth",
    "vid sidan av studier", "vid sidan av studierna",
    "driver du eget företag vid sidan av studier",
    "affärsinriktade studier", "ledarskap i affärs", "affärsinriktad",
    "utbytesstudier", "utbyte", "fältstudier",
    "studieresa", "studieresor",
    "vidarestudier", "fortsatta studier",
    "högskolestudier", "universitetsstudier",
    "uppsatstävling",
    "tävla med kandidat", "tävla med magister", "tävla med master",
    "studenttävling",
    "studerande", "studenter", "student",
    "lärjungar", "lärjunge", "elever",
]

WEAK_STUDENT_TERMS = [
    "studier", "utbildning", "studies",
    "education", "undervisning",
]

RESEARCH_BENEFICIARY_TERMS = [
    "till forskare", "åt forskare", "för forskare",
    "forskartjänst", "forskarstipendium", "forskarstipendier",
    "forskningsbidrag", "forskningsanslag",
    "forskarstuderande",
    "forskare vid", "forskare och",
    "for researchers", "research grant", "research scholarship",
    "researcher exchange", "sabbatical",
    "preferably a doctorate", "helst doktorsexamen",
    "individual researchers", "individuella forskare",
    "antagna till forskarutbildning",
    "studier efter avlagd doktorsexamen",
    "bedriver studier efter avlagd doktorsexamen",
]

RESEARCH_PRIMARY_PHRASES = [
    "främja vetenskaplig forskning",
    "främja forskning",
    "stödja forskning",
    "promote scientific research",
    "promote research",
    "support scientific research",
    "support research",
    "primarily to support scientific research",
    "huvudsakliga ändamål att främja forskning",
]

RESEARCH_STUDY_LEVELS = [
    "research", "doctoral", "forskning", "doktorsexamen",
    "forskarutbildning", "postdoc",
]

SWEDISH_PLACE_NAMES = {
    "trollhättan", "gävle", "lund", "malmö", "göteborg", "stockholm",
    "uppsala", "linköping", "örebro", "umeå", "jönköping", "norrköping",
    "helsingborg", "västerås", "borås", "sundsvall", "östersund",
    "karlstad", "växjö", "kalmar", "kristianstad", "halmstad",
    "luleå", "kiruna", "skellefteå", "falun", "borlänge",
    "visby", "hudiksvall", "härnösand", "nyköping", "eskilstuna",
    "norrtälje", "enköping", "tierp", "mora", "ludvika",
    "örnsköldsvik", "sollefteå", "kramfors", "ånge",
}

MEDICAL_EXPLICIT_TERMS = [
    "medicine studerande", "medicinstuderande", "medicinare",
    "medicine studerandes", "medicinska fakulteten",
    "karolinska institutet", "karolinska institutets", "karolinska",
    "medicinska högskolan",
    "läkarexamen", "läkarutbildning",
    "tandläkar", "tandläkarinstitutet", "tandläkarutbildning",
    "medicinsk forskning", "medicinsk vetenskaplig forskning",
    "medicinska området", "det medicinska området",
    "medicinsk", "medicinska", "medicinskt",
    "njurmedicinsk", "njurmedicin",
    "kirurgiska kliniken", "kirurgiska",
    "gynekologisk", "onkologi", "gynekologisk onkologi",
    "sjukvårdsverksamhet", "kvalificerad sjukvårdsverksamhet",
    "sjukvård", "kliniskt betydelsefull",
    "klinisk", "kliniskt", "kliniska",
    "sjöbefäl", "sjöbefälsskola", "sjöbefälsskolans",
    "naturvetenskapliga", "naturvetenskaplig",
    "tekniska gymnasiestudier",
]

MEDICAL_TERMS = [
    "medicine", "medical", "medicin", "medicinsk", "medicinska", "medicinskt",
    "medicinare", "medicinstuderande", "medicine studerande",
    "läkare", "läkarexamen", "läkarutbildning", "läkarprogrammet",
    "sjukvård", "healthcare", "health", "hälsa", "hälsovetenskap",
    "nursing", "omvårdnad", "sjuksköterska", "sjuksköterskeprogrammet",
    "tandvård", "dentistry", "dental", "tandläkare", "tandläkarutbildning",
    "farmaci", "pharmacy", "pharmaceutical", "läkemedel", "apotekare",
    "biomedicin", "biomedical", "biomedicinsk",
    "kirurgi", "surgery", "surgical", "kirurgisk",
    "klinisk", "kliniskt", "kliniska", "clinical",
    "patologi", "pathology", "onkologi", "oncology",
    "gynekologi", "gynekologisk", "pediatrik", "pediatrics",
    "psykiatri", "psychiatry", "neurologi", "neurology",
    "fysiologi", "physiology", "anatomi", "anatomy",
    "epidemiologi", "epidemiology",
    "folkhälsa", "public health",
    "veterinär", "veterinary",
    "karolinska", "karolinska institutet",
    "medicinsk forskning", "medical research",
    "sjukhus", "hospital",
    "rehabilitering", "rehabilitation",
    "geriatrik", "geriatrics",
    "reumatologi", "rheumatology",
    "njurmedicin", "njurmedicinsk",
    "kardiologi", "cardiology",
    "dermatologi", "dermatology",
]

NON_MEDICAL_DOMAIN_TERMS = [
    "juridik", "juridisk", "juridiska", "affärsjuridik", "rättsvetenskap",
    "law", "legal",
    "företagsekonomi", "handelshögskolan", "business administration",
    "maskinteknik", "mechanical engineering",
    "datateknik", "computer engineering", "programvaruteknik",
    "elektroteknik", "electrical engineering",
    "civilingenjör", "civilingenjörs",
    "byggteknik", "construction engineering",
    "arkitektur", "architecture",
    "musik", "music", "konstnärlig", "artistic",
    "teater", "theatre", "dans", "dance", "opera",
    "jordbruk", "agriculture", "lantbruk", "skogsbruk", "forestry",
    "sjöbefäl", "sjöfart", "nautisk",
]

INDIVIDUAL_ACCESSIBLE_MARKERS = [
    "stipendium", "stipendier", "stipendiat",
    "resestipendium", "resestipendier",
    "forskarstipendie", "forskarstipendium",
    "studiestipendium", "studiestipendier",
    "bidrag till enskilda",
    "bidrag till fysiska personer",
    "bidrag till person",
    "ekonomiskt stöd till",
    "ekonomiskt bidrag till",
    "anslag till enskilda",
    "anslag till fysiska",
    "åt studerande", "åt studenter",
    "åt forskare", "åt doktorand",
    "till studerande", "till studenter",
    "till forskare", "till doktorand",
    "till person", "till personer",
    "till enskild", "till enskilda",
    "ansökan", "ansöka", "sökande",
    "den sökande", "sökanden",
    "meriterade sökande",
    "välmeriterade sökande",
    "resor", "studieresa", "studieresor",
    "utlandsstudier", "utlandsvistelse",
    "utbyte", "utbytesstudier",
]

INSTITUTIONAL_ONLY_MARKERS = [
    "endast till institution",
    "enbart till institution",
    "anslag till universitetet",
    "anslag till högskolan",
    "anslag till fakulteten",
    "bidrag till institutionen",
    "bidrag till universitetet",
    "bidrag till högskolan",
    "lönekostnader", "lönekostnad",
    "avlöning av", "avlöna",
    "personalkostnader", "personalkostnad",
    "driftskostnader", "driftskostnad",
    "lokalkostnader", "lokalkostnad",
    "utrustning till institutionen",
    "inköp av utrustning",
    "laboratorieutrustning",
    "byggnation av",
    "renovering av",
    "finansiera professur",
    "inrätta professur",
    "upprätthålla professur",
    "gästprofessors verksamhet",
    "bibliotekets verksamhet",
    "inköp av böcker till",
    "samlingens underhåll",
    "ej till enskilda",
    "inte till enskilda",
    "ej personliga",
    "inte personliga stipendier",
]


STRONG_TECH_SINGLE_MATCH_TERMS = [
    "civilingenjör",
    "tekniska högskolan",
    "tekniska hogskolan",
    "teknisk forskning",
    "teknisk utbildning",
    "teknologer vid chalmers",
    "chalmers tekniska",
    "elmaskinteknik",
    "kraftelektronik",
    "produktionsteknik",
    "miljöteknik",
    "elektroteknik",
    "maskinteknik",
    "byggteknik",
    "programvaruteknik",
    "datateknik",
    "mekatronik",
    "fordonsteknik",
    "flygteknik",
    "rymdteknik",
    "energiteknik",
    "materialteknik",
    "bioteknik",
    "kemiteknik",
    "industriell ekonomi",
    "kemins och elektronikens",
    "kemins område",
    "elektronikens område",
    "skoglig och skogsindustriell",
    "skogsindustriell verksamhet",
    "skoglig verksamhet",
]


FORESTRY_NATURAL_RESOURCE_TERMS = [
    "skoglig", "skogsindustriell", "skogsindustri", "skogsbruk",
    "skogsvetenskap", "skogsforskning", "skogsnäring",
    "gruv", "gruvnäring", "mineral", "mineralnäring",
    "bergsbruk", "bergsindustri",
]



def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def contains_any(text: str, terms: List[str]) -> bool:
    t = normalize_text(text)
    return any(term in t for term in terms)


def contains_any_stem(text: str, terms: List[str], min_stem_len: int = 6) -> bool:
    t = normalize_text(text)
    for term in terms:
        if term in t:
            return True
        if len(term) >= min_stem_len:
            stem = term[:min_stem_len]
            if stem in t:
                return True
    return False
def resolve_municipality(municipality: str) -> str:
    """
    Maps any municipality input — English name, Swedish name,
    any casing — to the exact Swedish value stored in Pinecone.
    Returns the original string unchanged if no mapping found,
    so existing correct Swedish inputs are never broken.
    """
    if not municipality:
        return municipality
    key = municipality.strip().lower()
    return MUNICIPALITY_NAME_MAP.get(key, municipality.strip())


def match_tech_terms_word_boundary(text: str, terms: List[str]) -> List[str]:
    
    t = normalize_text(text)
    matched = []
    for term in terms:
        if ' ' in term:
            # Multi-word root: exact substring is safe (phrase is specific)
            if term in t:
                matched.append(term)
        else:
            pattern = re.compile(r'\b' + re.escape(term) + r'\w*', re.IGNORECASE)
            if pattern.search(t):
                matched.append(term)
    return matched


def count_matches(text: str, terms: List[str]) -> int:
    t = normalize_text(text)
    return sum(1 for term in terms if term in t)


def get_matched_terms(text: str, terms: List[str]) -> List[str]:
    """Returns the actual terms that matched. Used for debug traceability."""
    t = normalize_text(text)
    return [term for term in terms if term in t]


def combined_scholarship_text(sch: Dict[str, Any]) -> str:
    return normalize_text(" ".join([
        str(sch.get("Name", "")),
        str(sch.get("Purpose", "")),
        str(sch.get("Category", "")),
        str(sch.get("Study Level", ""))
    ]))


def scholarship_purpose_text(sch: Dict[str, Any]) -> str:
    return normalize_text(str(sch.get("Purpose", "")))


def _exclusion_purpose_text(sch: Dict[str, Any]) -> str:
    """
    Text used for EXCLUSION decisions — Name + Purpose ONLY.
    Do NOT include Study Level or Category.
    """
    return normalize_text(" ".join([
        str(sch.get("Name", "")),
        str(sch.get("Purpose", "")),
    ]))


def expand_user_query_for_embedding(user_purpose: str) -> str:
    text = normalize_text(user_purpose)
    expansions = []
    if any(k in text for k in ["finance", "finans", "economics", "ekonomi"]):
        expansions.extend(["business", "accounting", "management", "commerce",
                           "företagsekonomi", "handelshögskolan"])
    if any(k in text for k in ["law", "juridik", "legal", "rättsvetenskap"]):
        expansions.extend([
            "juridik", "juridiska studier", "rättsvetenskap", "jurist",
            "folkrätt", "affärsjuridik", "eg-rätt", "företagsjuridik",
            "sjörätt", "transporträtt", "stipendium juridik"
        ])
    if any(k in text for k in ["technology", "teknik", "engineering", "computer", "software"]):
        expansions.extend(["teknik", "ingenjör", "datavetenskap", "it", "software",
                           "civilingenjör", "teknisk"])
    if any(k in text for k in ["medicine", "medical", "medicin", "healthcare",
                                "health", "nursing", "pharmacy", "dental",
                                "läkare", "sjukvård", "hälsa"]):
        expansions.extend([
            "medicin", "medicinsk", "läkarutbildning", "sjukvård",
            "karolinska", "biomedicin", "klinisk", "hälsovetenskap",
            "farmaci", "tandvård", "stipendium medicin"
        ])
    if expansions:
        return f"{user_purpose} related fields: {', '.join(sorted(set(expansions)))}"
    return user_purpose


def safe_translate(text: str, source: str, target: str) -> str:
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception:
        return text


def is_law_relevant(text: str) -> bool:
    return contains_any(text, LAW_TERMS)


def is_user_seeking_law(user_purpose: str) -> bool:
    return contains_any(user_purpose, LAW_TERMS)


def get_user_domain(user_purpose: str) -> str:
    text = normalize_text(user_purpose)
    if is_user_seeking_law(text):
        return "law"
    if contains_any(text, BUSINESS_TERMS):
        return "business"
    if contains_any(text, TECHNOLOGY_TERMS):
        return "technology"
    if contains_any(text, MEDICAL_TERMS):
        return "medical"
    return "general"


def is_domain_match(text: str, user_purpose: str) -> bool:
    domain = get_user_domain(user_purpose)
    if domain == "law":
        return is_law_relevant(text)
    elif domain == "business":
        return contains_any(text, BUSINESS_TERMS)
    elif domain == "technology":
        return contains_any(text, TECHNOLOGY_TERMS)
    elif domain == "medical":
        return contains_any(text, MEDICAL_TERMS)
    return False


RESEARCH_USER_TERMS = [
    "research", "forskning", "doctoral", "doktorand", "phd", "ph.d",
    "postdoc", "postdoctoral", "forskarutbildning", "researcher",
    "forskare", "dissertation", "avhandling",
]


def is_research_user(user_purpose: str) -> bool:
    return contains_any(normalize_text(user_purpose), RESEARCH_USER_TERMS)


def is_strongly_student_facing(text: str) -> bool:
    return contains_any(text, STRONG_STUDENT_TERMS)


def has_undergrad_indicators(text: str) -> bool:
    return contains_any(text, UNDERGRAD_INDICATOR_TERMS)


def is_research_beneficiary(text: str) -> bool:
    return contains_any(text, RESEARCH_BENEFICIARY_TERMS)


def is_research_primary(text: str) -> bool:
    return contains_any(text, RESEARCH_PRIMARY_PHRASES)


def has_research_study_level(sch: Dict) -> bool:
    level = normalize_text(str(sch.get("Study Level", "")))
    return contains_any(level, RESEARCH_STUDY_LEVELS)


def _has_research_and_education_coexistence(text: str) -> bool:
    has_research = contains_any(text, SOFT_RESEARCH_TERMS)
    education_terms = [
        "utbildning", "undervisning", "studieverksamhet",
        "education", "teaching", "lärande",
        "studiestöd",
    ]
    has_education = contains_any(text, education_terms)
    return has_research and has_education


def _has_individual_grant_language(text: str) -> bool:
    individual_grant_phrases = [
        "delar ut bidrag", "delar ut stipendium",
        "bidrag och stipendium", "stipendium och bidrag",
        "bidrag till fysiska", "stipendium till fysiska",
        "ekonomiska bidrag", "ekonomiskt bidrag",
        "bidrag till enskilda", "anslag till enskilda",
    ]
    return contains_any(text, individual_grant_phrases)


def is_genuinely_dual_purpose(text: str) -> bool:
    has_dual_phrase = contains_any(text, DUAL_PURPOSE_PHRASES)
    has_broad_coexistence = _has_research_and_education_coexistence(text)

    if not has_dual_phrase and not has_broad_coexistence:
        return False

    has_strict_doctoral = contains_any(text, STRICT_RESEARCH_ONLY_TERMS)
    has_student = is_strongly_student_facing(text)
    has_undergrad = has_undergrad_indicators(text)

    if has_strict_doctoral and not has_student and not has_undergrad:
        return False

    return True


def has_thesis_student_terms(text: str) -> bool:
    return contains_any(text, THESIS_STUDENT_TERMS)


def is_faculty_wide_scholarship(text: str) -> bool:
    return contains_any(text, FACULTY_WIDE_TERMS)


def classify_scholarship(sch: Dict) -> str:
    
    text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    content_text = _exclusion_purpose_text(sch)
    has_undergrad = has_undergrad_indicators(purpose) or has_undergrad_indicators(text)
    strong_student = is_strongly_student_facing(purpose) or is_strongly_student_facing(text)
    dual = is_genuinely_dual_purpose(purpose)
    has_thesis = has_thesis_student_terms(text)
    has_faculty = is_faculty_wide_scholarship(text)
    research_beneficiary = is_research_beneficiary(purpose)
    research_primary = is_research_primary(purpose)
    research_level = has_research_study_level(sch)
    has_strict_doctoral = contains_any(content_text, STRICT_RESEARCH_ONLY_TERMS)
    has_soft_research = contains_any(content_text, SOFT_RESEARCH_TERMS)
    has_weak_student = contains_any(purpose, WEAK_STUDENT_TERMS)

    if has_undergrad:
        return "student"
    if has_thesis:
        return "student"
    if has_faculty and not has_strict_doctoral:
        return "student"
    if strong_student and not has_strict_doctoral:
        return "student"
    if has_strict_doctoral and not strong_student and not has_undergrad:
        return "research"
    if strong_student and has_strict_doctoral:
        return "mixed"
    if dual:
        return "mixed"
    if research_beneficiary and research_level:
        return "research"
    if research_primary and not strong_student and not has_undergrad:
        return "research"
    if research_beneficiary and has_soft_research and not strong_student:
        return "research"
    if has_soft_research and research_level and not strong_student and not has_undergrad:
        return "research"
    if has_soft_research and not has_weak_student and not strong_student and not has_undergrad:
        return "research"
    if has_soft_research and has_weak_student and research_primary:
        return "research"
    if has_soft_research and has_weak_student:
        return "mixed"

    return "neutral"


def _has_undergraduate_safe_harbor(text: str, purpose: str) -> bool:
    """CENTRAL SAFE HARBOR CHECK - used by all exclusion functions."""
    if has_undergrad_indicators(text):
        return True
    if has_thesis_student_terms(text):
        return True
    if is_faculty_wide_scholarship(text):
        return True
    if is_genuinely_dual_purpose(text) or is_genuinely_dual_purpose(purpose):
        return True
    if is_strongly_student_facing(text):
        return True
    return False


def _is_exclusively_doctoral(sch: Dict) -> Tuple[bool, str]:
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)

    if _has_undergraduate_safe_harbor(full_text, purpose):
        return False, ""

    strict_matches = get_matched_terms(excl_text, STRICT_RESEARCH_ONLY_TERMS)
    if strict_matches:
        return True, f"exclusively doctoral/postdoc (matched in purpose: {strict_matches})"

    advanced_matches = get_matched_terms(excl_text, ADVANCED_LEVEL_EXCLUSION_PHRASES)
    if advanced_matches:
        return True, f"advanced level minimum requirement (matched in purpose: {advanced_matches})"

    docent_matches = get_matched_terms(excl_text, DOCENT_EXCLUSIVE_TERMS)
    if docent_matches:
        return True, f"exclusively for docent position (matched in purpose: {docent_matches})"

    return False, ""


def _is_institution_support(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
  
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)
    name = normalize_text(str(sch.get("Name", "")))

    user_domain = get_user_domain(user_purpose)


    purpose_has_user_domain = False
    if user_domain == "law":
        purpose_has_user_domain = contains_any(purpose, LAW_TERMS)
    elif user_domain == "business":
        purpose_has_user_domain = contains_any(purpose, BUSINESS_TERMS)
    elif user_domain == "technology":
        purpose_has_user_domain = contains_any(purpose, TECHNOLOGY_TERMS)
    elif user_domain == "medical":
        purpose_has_user_domain = contains_any(purpose, MEDICAL_TERMS)

    if purpose_has_user_domain:

        hard_cost_markers = [
            "lönekostnader", "lönekostnad",
            "avlöning av en professor", "avlöning av en lärare",
            "finansiera professuren", "inrätta professur",
            "upprätthålla professur", "gästprofessors verksamhet",
            "inköp av böcker för seminariebiblioteket",
            "böcker för seminariebiblioteket",
        ]
        if not contains_any(excl_text, hard_cost_markers):
            return False, ""


    name_inst_matches = get_matched_terms(name, NAME_INSTITUTION_TERMS)
    if name_inst_matches:
        if contains_any(purpose, DIRECT_STUDENT_BENEFIT_OVERRIDES):
            return False, ""
        return True, f"name indicates institution support (matched in name: {name_inst_matches})"

    if _has_undergraduate_safe_harbor(full_text, purpose):
        return False, ""

    if any(word in normalize_text(user_purpose)
           for word in ["professor", "faculty", "fakultet"]):
        return False, ""

    inst_matches = get_matched_terms(excl_text, INSTITUTION_SUPPORT_TERMS)
    if inst_matches:
        return True, f"institution support - no student benefit (matched: {inst_matches})"

    cost_matches = get_matched_terms(excl_text, INSTITUTION_COST_TERMS)
    if cost_matches:
        return True, f"institutional costs - no student benefit (matched: {cost_matches})"

    docent_matches = get_matched_terms(excl_text, DOCENT_EXCLUSIVE_TERMS)
    if docent_matches:
        return True, f"docent salary/position - institution support (matched: {docent_matches})"

    return False, ""


def should_exclude_research_doctoral(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)

    if is_research_user(user_purpose):
        return False, ""

    if _has_undergraduate_safe_harbor(full_text, purpose):
        return False, ""

    if is_domain_match(excl_text, user_purpose):
        return False, ""

    if _has_research_and_education_coexistence(excl_text):
        return False, ""

    if _has_individual_grant_language(excl_text):
        return False, ""

    if contains_any(excl_text, INDIVIDUAL_ACCESSIBLE_MARKERS):
        return False, ""

    is_doctoral, reason = _is_exclusively_doctoral(sch)
    if is_doctoral:
        return True, reason

    is_undergrad_user = contains_any(user_purpose, UNDERGRAD_TERMS)

    if is_undergrad_user and contains_any(excl_text, SOFT_RESEARCH_TERMS):
        inst_only_matches = get_matched_terms(excl_text, INSTITUTIONAL_ONLY_MARKERS)
        if inst_only_matches:
            return True, f"institutional-only research fund (matched: {inst_only_matches[:5]})"
        return False, ""

    return False, ""


def should_exclude_entity_type(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
   
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)
    name = normalize_text(str(sch.get("Name", "")))
    user_domain = get_user_domain(user_purpose)

    # MASTER DOMAIN SAFE HARBOR — only exit early if scholarship also has
    # direct scholarship language. Institutional funds have domain terms
    # but never contain stipendium/bidrag/ansökan etc.
    if user_domain == "law" and is_law_relevant(excl_text):
        if contains_any(excl_text, STRONG_DIRECT_SCHOLARSHIP_TERMS):
            return False, ""
    if user_domain == "business" and contains_any(excl_text, BUSINESS_TERMS):
        if contains_any(excl_text, STRONG_DIRECT_SCHOLARSHIP_TERMS):
            return False, ""
    if user_domain == "technology" and contains_any(excl_text, TECHNOLOGY_TERMS):
        if contains_any(excl_text, STRONG_DIRECT_SCHOLARSHIP_TERMS):
            return False, ""
    if user_domain == "medical" and contains_any(excl_text, MEDICAL_TERMS):
        if contains_any(excl_text, STRONG_DIRECT_SCHOLARSHIP_TERMS):
            return False, ""

    if user_domain == "law":

        tech_cross_domain_safe = [
            "ekonomisk och teknisk", "teknisk och ekonomisk",
            "ekonomi och teknik", "teknik och ekonomi",
            "samhällsvetenskaplig och teknisk",
        ]
        if not contains_any(excl_text, tech_cross_domain_safe):
            strong_tech_matches = match_tech_terms_word_boundary(excl_text, STRONG_TECH_SINGLE_MATCH_TERMS)
            if strong_tech_matches:
                return True, f"strong tech/engineering domain for law user (matched: {strong_tech_matches[:3]})"

        tech_general_matches = get_matched_terms(excl_text, TECHNOLOGY_TERMS)
        if len(tech_general_matches) >= 2:
            if not contains_any(excl_text, LAW_TERMS):
                return True, f"tech/engineering domain for law user ({len(tech_general_matches)} matches: {tech_general_matches[:3]})"

        medical_matches = get_matched_terms(excl_text, MEDICAL_EXPLICIT_TERMS)
        if medical_matches:
            if not contains_any(excl_text, LAW_TERMS):
                return True, f"explicit medical/non-law domain for law user (matched: {medical_matches[:5]})"

    if user_domain == "medical":
        law_explicit = [
            "juridik", "juridisk", "juridiska", "affärsjuridik",
            "rättsvetenskap", "jurist", "juridiska fakulteten",
            "sjörätt", "transporträtt",
        ]
        law_matches = get_matched_terms(excl_text, law_explicit)
        if law_matches:
            if not contains_any(excl_text, MEDICAL_TERMS):
                return True, f"explicit law domain for medical user (matched: {law_matches[:5]})"

    if user_domain == "business":
        medical_matches = get_matched_terms(excl_text, MEDICAL_EXPLICIT_TERMS)
        if medical_matches:
            if not contains_any(excl_text, BUSINESS_TERMS):
                return True, f"explicit medical domain for business user (matched: {medical_matches[:5]})"

    if user_domain == "technology":
        medical_matches = get_matched_terms(excl_text, MEDICAL_EXPLICIT_TERMS)
        if medical_matches:
            if not contains_any(excl_text, TECHNOLOGY_TERMS):
                return True, f"explicit medical domain for technology user (matched: {medical_matches[:5]})"

    # ============================================================
    # CHECK 1: Institution Support (Rule 2)
    # ============================================================
    is_inst, inst_reason = _is_institution_support(sch, user_purpose)
    if is_inst:
        return True, inst_reason

    # ============================================================
    # CHECK 2: Wrong Educational Level (Rule 4)
    # ============================================================
    below_university_only_terms = [
        "elev i grundskolan", "grundskolan",
        "grundskoleelev", "grundskoleelever",
        "naturbruksgymnasiet", "naturbruk",
        "gymnasieskolas samfond",
        "lärjunge", "lärjungar",
        "realskolan", "realskolans",
        "läroverket", "läroverk",
        "abiturient",
    ]
    name_school_patterns = [
        "skolfond", "skolas stipendiestiftelse", "skolas samfond",
        "skolans stipendie", "skolans fond",
    ]
    gymnasium_only_terms = [
        "gymnasieelever", "gymnasieelev", "gymnasieskolan", "gymnasiet",
    ]
    university_pathway_terms = [
        "högskola", "universitet", "universitetsstudier", "högskolestudier",
        "sökt utbildning på högskola", "sökt utbildning på universitet",
        "fortsätta studera", "vidarestudier vid",
        "högskoleutbildning", "universitetsutbildning",
    ]

    if "studentexamen" in excl_text:
        if not contains_any(excl_text, university_pathway_terms):
            return True, "below university level only (matched: ['studentexamen'] with no university pathway)"

    if contains_any(excl_text, below_university_only_terms):
        if not contains_any(excl_text, university_pathway_terms):
            matched = get_matched_terms(excl_text, below_university_only_terms)
            return True, f"below university level only (matched: {matched})"

    if contains_any(name, name_school_patterns):
        if not contains_any(excl_text, university_pathway_terms):
            matched = get_matched_terms(name, name_school_patterns)
            return True, f"below university level only (school name pattern: {matched})"

    if contains_any(excl_text, gymnasium_only_terms):
        if not contains_any(excl_text, university_pathway_terms):
            matched = get_matched_terms(excl_text, gymnasium_only_terms)
            return True, f"gymnasium only with no university pathway (matched: {matched})"

    # ============================================================
    # CHECK 2.5: Entrepreneurship Support Exclusion
    # ============================================================
    user_text = normalize_text(user_purpose)
    if not contains_any(user_text, ["entrepren", "startup", "drivhus", "inkubat"]):
        if contains_any(excl_text, ENTREPRENEURSHIP_SUPPORT_TERMS):
            matched = get_matched_terms(excl_text, ENTREPRENEURSHIP_SUPPORT_TERMS)
            return True, f"entrepreneurship support (matched: {matched})"

    # ============================================================
    # CHECK 3: Domain mismatch — STANDARD PATH
    # ============================================================
    has_scholarship_terms = contains_any(excl_text, STRONG_DIRECT_SCHOLARSHIP_TERMS)

    # LAW USER
    if user_domain == "law":
        is_domain_scholarship = is_law_relevant(excl_text)
        if not is_domain_scholarship:
            non_law_matches = get_matched_terms(excl_text, NON_LAW_DOMAIN_TERMS)
            if len(non_law_matches) >= 2:
                matched = get_matched_terms(excl_text, NON_LAW_DOMAIN_TERMS)
                return True, f"non-law domain mismatch ({len(non_law_matches)} matches: {matched[:5]})"

            off_topic_single_terms = [
                "flyg", "rymd", "luftfart", "aviation", "aerospace",
                "restaurang", "livsmedel", "måltid", "matvetenskap",
                "romanska språk", "slaviska språk", "nordiska språk",
                "östasiatisk", "engelska språket", "germansk",
                "lingvistik", "språkvetenskap",
                "byggande", "boende", "samhällsbyggnad",
                "strukturell", "structural engineering",
                "idrott", "sport", "idrottsvetenskap",
                "sjöutbildning", "sjöingenjör", "sjökapten",
                "mode", "textil", "design",
                "omvårdnad", "sjukskötersk",
            ]
            if contains_any(excl_text, off_topic_single_terms):
                matched = get_matched_terms(excl_text, off_topic_single_terms)
                return True, f"off-topic subject for law user (matched: {matched[:3]})"

    # BUSINESS USER
    if user_domain == "business":
        if contains_any(excl_text, LAW_TERMS) and not contains_any(excl_text, BUSINESS_TERMS):
            if _is_domain_specific(excl_text, LAW_TERMS):
                matched = get_matched_terms(excl_text, LAW_TERMS)
                return True, f"law domain mismatch - business user (matched: {matched})"
        if contains_any(excl_text, NON_BUSINESS_DOMAIN_TERMS) and not contains_any(excl_text, BUSINESS_TERMS):
            if _is_domain_specific(excl_text, NON_BUSINESS_DOMAIN_TERMS):
                if not has_scholarship_terms:
                    matched = get_matched_terms(excl_text, NON_BUSINESS_DOMAIN_TERMS)
                    return True, f"non-business domain mismatch (matched: {matched})"
                non_biz_count = count_matches(excl_text, NON_BUSINESS_DOMAIN_TERMS)
                biz_count = count_matches(excl_text, BUSINESS_TERMS)
                if non_biz_count > biz_count + 2:
                    matched = get_matched_terms(excl_text, NON_BUSINESS_DOMAIN_TERMS)
                    return True, f"non-business domain mismatch - primary domain (matched: {matched})"

    # TECHNOLOGY USER
    if user_domain == "technology":
        if contains_any(excl_text, NON_TECH_DOMAIN_TERMS) and not contains_any(excl_text, TECHNOLOGY_TERMS):
            if _is_domain_specific(excl_text, NON_TECH_DOMAIN_TERMS):
                if not has_scholarship_terms:
                    matched = get_matched_terms(excl_text, NON_TECH_DOMAIN_TERMS)
                    return True, f"non-tech domain mismatch (matched: {matched})"

    # MEDICAL USER
    if user_domain == "medical":
        non_med_explicit = [
            "juridik", "juridisk", "juridiska", "affärsjuridik",
            "rättsvetenskap", "law", "legal",
            "sjörätt", "transporträtt", "folkrätt",
            "civilingenjör", "maskinteknik", "datateknik",
            "elektroteknik", "byggteknik", "programvaruteknik",
            "sjöbefäl", "sjöfart", "nautisk",
        ]
        if contains_any(excl_text, non_med_explicit) and not contains_any(excl_text, MEDICAL_TERMS):
            non_med_count = count_matches(excl_text, non_med_explicit)
            if non_med_count >= 2:
                matched = get_matched_terms(excl_text, non_med_explicit)
                return True, f"non-medical domain mismatch ({non_med_count} matches: {matched[:5]})"

        if contains_any(excl_text, NON_MEDICAL_DOMAIN_TERMS):
            non_med_count = count_matches(excl_text, NON_MEDICAL_DOMAIN_TERMS)
            if non_med_count >= 2:
                if has_scholarship_terms and non_med_count < 4:
                    pass
                else:
                    matched = get_matched_terms(excl_text, NON_MEDICAL_DOMAIN_TERMS)
                    return True, f"non-medical domain mismatch ({non_med_count} matches: {matched[:5]})"

    return False, ""



def should_exclude_study_level_mismatch(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)
    classification = classify_scholarship(sch)

    is_undergrad_user = contains_any(normalize_text(user_purpose), UNDERGRAD_TERMS)
    _is_research_user = is_research_user(user_purpose)

    if is_undergrad_user and classification == "research":
    
        purpose_only = scholarship_purpose_text(sch)
        if is_domain_match(purpose_only, user_purpose):
            return False, ""

        # Non-domain research scholarship for undergrad user
        if _has_research_and_education_coexistence(excl_text):
            return False, ""
        if _has_individual_grant_language(excl_text):
            return False, ""
        if is_strongly_student_facing(full_text):
            return False, ""

        if contains_any(excl_text, INDIVIDUAL_ACCESSIBLE_MARKERS):
            return False, ""

        return True, f"research-only scholarship for undergrad user (classification: research)"

    if _is_research_user and classification == "student":
      
        if is_domain_match(purpose, user_purpose):  
            return False, ""
        if is_faculty_wide_scholarship(full_text):
            return False, ""
        if has_thesis_student_terms(full_text):
            return False, ""

        undergrad_only_signals = [
            "gymnasieelever", "gymnasieelev",
            "grundskolan", "grundskoleelev",
            "årskurs 1", "årskurs 2", "årskurs 3",
            "lärjungar", "lärjunge",
            "elev vid borgarskolan", "elev vid",
        ]
        if contains_any(excl_text, undergrad_only_signals):
            matched = get_matched_terms(excl_text, undergrad_only_signals)
            return True, f"undergrad-only scholarship for research user (matched: {matched})"

        return False, ""

    return False, ""

def should_exclude_gender_mismatch(sch: Dict, gender: str) -> Tuple[bool, str]:
    if not gender:
        return False, ""

    excl_text = _exclusion_purpose_text(sch)

    FEMALE_ONLY_TERMS = [
        "kvinnlig", "kvinnliga", "kvinna", "kvinnor",
        "för kvinnor", "only for women", "female only",
        "damer", "damernas",
    ]
    MALE_ONLY_TERMS = [
        "manlig", "manliga", "för män", "för man",
        "only for men", "male only",
        "herrar", "herrarna",
    ]

    # Normalize gender to English equivalents (handle Swedish: "Kvinna"→"female", "Man"→"male")
    gender_lower = gender.lower()
    if gender_lower in ["kvinna", "female", "woman", "f"]:
        is_female = True
        is_male = False
    elif gender_lower in ["man", "male", "m"]:
        is_male = True
        is_female = False
    else:
        # Unknown gender value - don't exclude
        return False, ""

    if is_male:
        matched = get_matched_terms(excl_text, FEMALE_ONLY_TERMS)
        if matched:
            return True, f"female-only scholarship for male user (matched: {matched})"

    elif is_female:
        matched = get_matched_terms(excl_text, MALE_ONLY_TERMS)
        if matched:
            return True, f"male-only scholarship for female user (matched: {matched})"

    return False, ""


def _is_domain_specific(text: str, domain_terms: List[str]) -> bool:
    t = normalize_text(text)
    match_count = sum(1 for term in domain_terms if term in t)
    return match_count >= 3


def _is_strongly_domain_specific(text: str, domain_terms: List[str]) -> bool:
    t = normalize_text(text)
    match_count = sum(1 for term in domain_terms if term in t)
    return match_count >= 5


def compute_entity_bonus(sch: Dict, user_purpose: str) -> float:
    bonus = 0.0
    text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    is_ug = contains_any(user_purpose, UNDERGRAD_TERMS)
    _is_res_user = is_research_user(user_purpose)
    classification = classify_scholarship(sch)

    if contains_any(user_purpose, BUSINESS_TERMS) and contains_any(text, BUSINESS_SCHOOL_STUDENT_TERMS):
        bonus += 0.35
    if contains_any(text, STRONG_DIRECT_SCHOLARSHIP_TERMS):
        bonus += 0.15
    if is_user_seeking_law(user_purpose) and is_law_relevant(text):
        bonus += 0.25
    if contains_any(user_purpose, BUSINESS_TERMS) and contains_any(text, BUSINESS_TERMS):
        bonus += 0.20
    if contains_any(user_purpose, TECHNOLOGY_TERMS):
        purpose_only = scholarship_purpose_text(sch)
        if contains_any(purpose_only, TECHNOLOGY_TERMS):
           
            bonus += 0.20
        elif contains_any(text, TECHNOLOGY_TERMS):
           
            bonus += 0.05
    if contains_any(user_purpose, MEDICAL_TERMS) and contains_any(text, MEDICAL_TERMS):
        bonus += 0.25

    if is_ug and classification == "student":
        bonus += 0.30
    elif is_ug and (is_strongly_student_facing(purpose) or is_strongly_student_facing(text)):
        bonus += 0.25

    if is_ug and is_strongly_student_facing(text) and is_domain_match(text, user_purpose):
        bonus += 0.20
    if is_ug and has_undergrad_indicators(text):
        bonus += 0.15

    if is_ug and classification == "research":
        bonus -= 0.35
    elif is_ug and classification == "mixed":
        bonus -= 0.10
    if is_ug and contains_any(text, ENTREPRENEURSHIP_SUPPORT_TERMS):
        bonus -= 0.50

    if _is_res_user:
        if classification == "research":
            bonus += 0.35
        elif classification == "mixed":
            bonus += 0.15
        elif classification == "student":
            bonus -= 0.15

        if is_research_beneficiary(purpose) or is_research_beneficiary(text):
            bonus += 0.15
        if has_research_study_level(sch):
            bonus += 0.10

    return round(bonus, 3)


def compute_soft_score(sch: Dict, purpose: str) -> float:
    ct = combined_scholarship_text(sch)
    pt = normalize_text(purpose)
    return round(((0.55 * fuzz.token_sort_ratio(pt, ct)) +
                  (0.45 * fuzz.partial_ratio(pt, ct))) / 100, 3)


def semantic_prefilter(sch: Dict, user_purpose: str) -> bool:
    score = sch.get("Adjusted Score", 0)
    text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)

    _is_res_user = is_research_user(user_purpose)

    if is_domain_match(text, user_purpose) and is_strongly_student_facing(text):
        return score >= 0.28
    if is_domain_match(text, user_purpose):
        return score >= 0.30 if _is_res_user else score >= 0.33

    if _is_res_user:
        cls = classify_scholarship(sch)
        if cls == "research":
            return score >= 0.30
        elif cls == "mixed":
            return score >= 0.33

    return score >= 0.38 if contains_any(user_purpose, UNDERGRAD_TERMS) else score >= 0.40

def llm_filter_scholarships(
    user_purpose,
    gender,
    scholarships,
    oai_client,
    debug=True,
    custom_system_prompt=None,
    min_results=MIN_RESULTS,
    user_type=None
):
 
    gender_rule = ""
    # Handle both English and Swedish gender values
    gender_lower = gender.lower() if gender else ""
    if gender_lower in ["male", "man"]:
        gender_rule = "\nGENDER RULE: User is male. Exclude scholarships explicitly for women only."
    elif gender_lower in ["female", "kvinna", "woman"]:
        gender_rule = "\nGENDER RULE: User is female. Exclude scholarships explicitly for men only."

    user_domain    = get_user_domain(user_purpose)
    is_undergrad   = contains_any(user_purpose, UNDERGRAD_TERMS)
    _is_res_user   = is_research_user(user_purpose)
    is_org_user    = user_type and user_type.lower() in ["organization", "organisation", "idrottsförening"]

    if is_org_user:
        if custom_system_prompt:
            system_prompt = custom_system_prompt.format(
                user_purpose=user_purpose,
                gender_rule=gender_rule,
                min_results=min_results
            )
        else:
            system_prompt = f"""You are a scholarship relevance filter for an ORGANISATION applicant.
The user is a förening, klubb, or legal entity (juridisk person) applying for funding.
Your job is to decide which scholarships this organisation can realistically apply for.

USER PURPOSE: "{user_purpose}"
APPLICANT TYPE: ORGANISATION (förening, klubb, juridisk person)

===============================================
STEP 1 -- RECIPIENT TYPE CHECK (Highest Priority)
===============================================
The single most important question is: WHO receives the money?

INCLUDE (strong match) if the scholarship purpose explicitly mentions
ANY of the following as the recipient or eligible applicant:
  - förening, föreningar, idrottsförening, idrottsföreningar
  - klubb, klubbar, sportförening, sportföreningar
  - juridiska personer, juridisk person
  - organisationer, organisation, sammanslutning, sammanslutningar
  - verksamhetsstöd, verksamhetsbidrag, föreningsbidrag, föreningsstöd
  - utrustning (till förening eller klubb)
  - utrustningsbidrag, träningsläger, lägerbidrag
  - ungdomsverksamhet (where the ORGANISATION runs the activity)
  - ideell förening, ideella föreningar
  - lokala idrottssällskap, lokala föreningar
  - "för sin verksamhet", "för verksamheten"
  - lag, enskilda lag (as an organisation-level team, not individual)

INCLUDE (broad match — no individual-only restriction found):
  - Scholarships about "idrott", "sport", "kultur", or "ungdomsverksamhet"
    that do NOT name individual persons as the sole recipients
  - Scholarships where the purpose is broad enough that a förening
    could realistically apply as the legal entity receiving funds
  - Scholarships mentioning "bidrag till" without specifying only individuals

===============================================
STEP 2 -- EXCLUDE INDIVIDUAL-ONLY SCHOLARSHIPS
===============================================
EXCLUDE only when ALL THREE conditions below are true:

  CONDITION A — The scholarship purpose uses INDIVIDUAL recipient language:
    One or more of these terms appears AND refer to the scholarship recipient:
    - ungdomar / ungdom (youth as direct recipients of money)
    - elev / elever (school students as recipients)
    - studerande / studenter (university students as recipients)
    - talanger / lovande talanger (talented individuals as recipients)
    - en ung person / unga personer (specific individuals)
    - individuella sökande / enskilda sökande
    - gymnast / spelare / idrottsutövare (individual athletes as recipients)
    - barn (individual children as direct recipients)
    - person / personer (when named as the only recipient type)

  CONDITION B — The scholarship has NO organisational pathway:
    None of these terms appear anywhere in the purpose:
    - förening, klubb, organisation, sammanslutning
    - juridiska personer, juridisk person
    - verksamhetsstöd, föreningsbidrag, verksamhetsbidrag
    - "för sin verksamhet", "för verksamheten"
    - utrustning, läger, lägerbidrag

  → EXCLUDE only if BOTH conditions (A + B) are satisfied.
  → If even ONE condition is missing → INCLUDE. Let reranker sort it.

===============================================
STEP 3 -- HARD EXCLUDE (Always Irrelevant)
===============================================
ALWAYS EXCLUDE these regardless of anything else:
  - Professorships, lectureships, named academic chair positions
  - Pure medical or scientific research funds with no sport/culture link
  - Scholarships requiring active university enrollment as individual
  - Scholarships exclusively for study trips abroad by individuals
  - Scholarships for individual artistic education (music, violin, art)
  - Scholarships tied to a specific named school's graduating class
  - Foundations whose PRIMARY purpose is environmental sustainability,
    climate, natural resources, or social development causes AND have
    no mention of sport, idrott, kultur, or the user's activity area
  - Any foundation where the core mission has zero overlap with the
    user's stated activity — if the user mentions a sport, exclude
    foundations that are entirely about a different field with no
    possible connection to that sport or physical activity
  - Scholarships tied to a specific named school's graduating class{gender_rule}

===============================================
STEP 4 -- DOUBT RULE (Default Action)
===============================================
YOUR DEFAULT ACTION IS ALWAYS: INCLUDE

Only exclude when you are CERTAIN that:
  1. The scholarship money goes exclusively to individual persons
  2. There is zero pathway for an organisation to apply
  3. The scholarship requires individual personal criteria

If you are uncertain about any of these three → INCLUDE.
The reranker handles the sorting. Your job is to keep the candidate pool
wide enough that relevant org-applicable scholarships are not lost.

===============================================
OUTPUT FORMAT
===============================================
Return ONLY a JSON array — no text, no markdown, no explanation:
[{{"index": 0, "relevance": "relevant"}}, {{"index": 1, "relevance": "irrelevant"}}]"""

        scholarship_list = "\n".join([
            f"[{i}] {s['Name']}: {s['Purpose'][:400]}"
            for i, s in enumerate(scholarships)
        ])

        user_prompt = (
            f"Evaluate these scholarships for an ORGANISATION (förening/klubb): \"{user_purpose}\"\n\n"
            f"Remember: The applicant is an organisation, not an individual person.\n"
            f"Scholarships that only fund individual ungdomar, elever, or studerande\n"
            f"should be excluded UNLESS they also mention förening, klubb, or juridiska personer.\n\n"
            f"Scholarships:\n{scholarship_list}\n\n"
            f"Minimum {min_results} relevant results required. "
            f"Return the JSON array now."
        )

        response = oai_client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            seed=42,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ]
        )

        try:
            raw         = response.choices[0].message.content.strip()
            start       = raw.index("[")
            end         = raw.rindex("]") + 1
            decisions   = json.loads(raw[start:end])
            rel_indices = {
                d["index"] for d in decisions
                if isinstance(d, dict) and d.get("relevance") == "relevant"
            }
            rel_indices = {i for i in rel_indices if 0 <= i < len(scholarships)}
            final_list  = [scholarships[i] for i in sorted(rel_indices)]

            if len(final_list) < min_results:
                if debug:
                    print(f"\n[SAFETY NET ORG] LLM returned {len(final_list)} — padding to {min_results}")

                included_names  = {s["Name"] for s in final_list}
                org_terms       = [
                    "förening", "föreningar", "klubb", "klubbar",
                    "juridiska personer", "juridisk person",
                    "verksamhetsstöd", "föreningsbidrag", "ideell förening",
                    "idrottsförening", "ungdomsverksamhet"
                ]
                org_padding = [
                    s for s in scholarships
                    if s["Name"] not in included_names
                    and contains_any(combined_scholarship_text(s), org_terms)
                ]
                remaining_padding = [
                    s for s in scholarships
                    if s["Name"] not in included_names
                    and s["Name"] not in {x["Name"] for x in org_padding}
                ]
                needed     = min_results - len(final_list)
                padding    = (org_padding + remaining_padding)[:needed]
                final_list = final_list + padding

                if debug:
                    print(f"[SAFETY NET ORG] Padded to {len(final_list)} results")

            if debug:
                excluded = [s for i, s in enumerate(scholarships) if i not in rel_indices]
                print(f"\n{'='*60}")
                print(f"[LLM FILTER ORG] INCLUDED ({len(final_list)}):")
                print(f"{'='*60}")
                for s in final_list:
                    cls = classify_scholarship(s)
                    print(f"  [{cls:>8}] {s['Name']}")
                    print(f"            Purpose: {s['Purpose'][:200]}")
                    print(f"  {'-'*56}")
                print(f"\n{'='*60}")
                print(f"[LLM FILTER ORG] EXCLUDED ({len(excluded)}):")
                print(f"{'='*60}")
                for s in excluded:
                    cls = classify_scholarship(s)
                    print(f"  [{cls:>8}] {s['Name']}")
                    print(f"            Purpose: {s['Purpose'][:200]}")
                    print(f"  {'-'*56}")

            return final_list

        except Exception as e:
            if debug:
                print(f"[LLM FILTER ORG] FAILED: {e} — returning all candidates unchanged")
            return scholarships

    if is_undergrad:
        study_level_context = "UNDERGRADUATE student (bachelor/kandidat level)"
        study_level_rules = """
STUDY LEVEL RULES FOR UNDERGRADUATE USER:
  INCLUDE scholarships that:
    - Target studerande, studenter, kandidat, bachelor, grundnivå
    - Are open to all university students (no level restriction)
    - Mention both students AND researchers (dual-purpose is valid)
    - Fund travel, exchange, or thesis work for students

  EXCLUDE scholarships that:
    - Exclusively fund doktorand, postdoc, or forskare
    - Require completed doctoral degree
    - Fund research positions with no student pathway
    - Are purely for teaching staff or academic personnel

  BORDERLINE CASES:
    - Mentions "forskning" but also "studerande" → INCLUDE
    - Mentions "vetenskaplig" but funds students → INCLUDE
    - Mentions "forskning och utbildning" → INCLUDE (dual purpose)
    - Mentions ONLY "forskare" with no student mention → EXCLUDE"""

    elif _is_res_user:
        study_level_context = "RESEARCHER (doctoral/postdoc level)"
        study_level_rules = """
STUDY LEVEL RULES FOR RESEARCHER USER:
  INCLUDE scholarships that:
    - Target forskare, doktorand, postdoc, PhD, doctoral
    - Fund scientific research or vetenskaplig forskning
    - Are dual-purpose (students + researchers both valid)
    - Fund research travel, sabbaticals, or research visits

  ALSO INCLUDE (lower priority but valid):
    - General student scholarships open to all levels
    - Domain-specific scholarships even if undergraduate-focused

  EXCLUDE scholarships that:
    - Are exclusively for primary or secondary school students
    - Have no connection to university-level study or research"""

    else:
        study_level_context = "UNSPECIFIED level"
        study_level_rules = """
STUDY LEVEL RULES FOR UNSPECIFIED USER:
  Treat all study levels as eligible.
  Include scholarships for students, researchers, and mixed purposes.
  Only exclude clearly wrong-domain scholarships.

INSTITUTIONAL FUND RULE:
  EXCLUDE scholarships that primarily fund research infrastructure,
  institutional operations, or academic department activities
  AND have no direct personal application pathway for individuals.

  Signals that confirm INSTITUTIONAL (→ EXCLUDE):
    - "att skapa en institution", "institutionens verksamhet"
    - "främja forskning" or "stödja forskning" as the SOLE purpose
    - "jubileumsfond" funding research rather than student stipendier
    - No mention of ansökan, sökande, or individual application
    - No explicit amount per recipient or number of recipients
    - Purpose describes supporting the institution itself, not students at it

  INCLUDE if the scholarship also contains:
    - stipendium, stipendier, bidrag, scholarship, grant
    - ansökan, sökande, apply
    - explicit recipient count or amount per person"""


    domain_rules = {
        "law": """DOMAIN RULES FOR LAW USER:
  INCLUDE if scholarship mentions:
    juridik, juridisk, juridiska, folkrätt, EG-rätt, affärsjuridik,
    sjörätt, transporträtt, rättsvetenskap, jurist, juriststudent,
    juridiska fakulteten, handelsrätt, skatterätt, civilrätt
  INCLUDE ALWAYS: general student scholarships open to all fields
  EXCLUDE ONLY IF: explicitly restricted to medicine, engineering,
    music, agriculture, or maritime with zero law relevance""",

        "business": """DOMAIN RULES FOR BUSINESS USER:
  INCLUDE if scholarship mentions:
    ekonomi, företagsekonomi, handelshögskolan, civilekonom,
    nationalekonomi, handel, marknadsföring, redovisning, finance,
    handelsprogrammet, ekonomistudent, business, management
  INCLUDE ALWAYS: general student scholarships open to all fields
  EXCLUDE ONLY IF: explicitly restricted to pure law, medicine,
    music, agriculture with zero business relevance""",

        "technology": """DOMAIN RULES FOR TECHNOLOGY USER:
  INCLUDE if scholarship mentions:
    teknik, teknisk, civilingenjör, ingenjör, datavetenskap,
    datateknik, IT, software, KTH, Chalmers, elektroteknik,
    maskinteknik, tekniska fakulteten, engineering
  INCLUDE ALWAYS: general student scholarships open to all fields
  EXCLUDE ONLY IF: explicitly restricted to law, medicine,
    music, agriculture with zero technology relevance""",

        "medical": """DOMAIN RULES FOR MEDICAL USER:
  INCLUDE if scholarship mentions:
    medicin, medicinsk, läkare, sjukvård, karolinska, biomedicin,
    klinisk, farmaci, tandläkare, sjuksköterska, hälsovetenskap,
    läkarprogrammet, healthcare, nursing
  INCLUDE ALWAYS: general student scholarships open to all fields
  EXCLUDE ONLY IF: explicitly restricted to law, engineering,
    music, agriculture with zero medical relevance""",
    }

    domain_context = domain_rules.get(
        user_domain,
        "GENERAL USER: Include all student-facing and research-relevant scholarships."
    )

    domain_context = domain_rules.get(
        user_domain,
        "GENERAL USER: Include all student-facing and research-relevant scholarships."
    )

    if custom_system_prompt:
        system_prompt = custom_system_prompt.format(
            user_purpose=user_purpose,
            study_level_context=study_level_context,
            study_level_rules=study_level_rules,
            domain_context=domain_context,
            gender_rule=gender_rule,
            min_results=min_results
        )
    else:
        system_prompt = f"""You are a scholarship relevance filter. Your job is to decide which scholarships are relevant for this user.

USER PURPOSE: "{user_purpose}"
STUDY LEVEL CONTEXT: {study_level_context}
{f'''
GENDER RULE — APPLY BEFORE ANYTHING ELSE
{gender_rule.strip()}
Any scholarship with an explicit gender restriction that does not
match the user MUST be marked irrelevant. This overrides all other rules.
Check every scholarship for "kvinnlig", "kvinnliga", "manlig", "manliga"
before evaluating domain or level.
''' if gender_rule else ''}

===============================================
STEP 1 -- SUBJECT + STUDY LEVEL MATCH (Highest Priority)
===============================================
First, identify scholarships that DIRECTLY match the user's subject AND study level.
These must be ranked and included first before anything else.

INCLUDE if the scholarship purpose:
  - Explicitly names the user's subject (e.g. law, economics, technology, engineering, medicine)
  - OR targets students at a relevant faculty, school, or university program
  - OR mentions the user's study level (bachelor, grundniva, kandidat, undergraduate, doctoral, postdoc)

RESEARCH LANGUAGE RULE -- CRITICAL:
  A scholarship may contain words like "forskning", "vetenskaplig", "utbildning och forskning".
  Do NOT auto-exclude these. Instead, ask: WHO receives the money?

  -> If it funds STUDENTS (studerande, elever, bachelor, kandidat, grundniva) -> INCLUDE for undergrad users
  -> If it funds RESEARCHERS only (forskare, postdoc, doktorand, PhD, dissertation) -> INCLUDE for research users, EXCLUDE for undergrad users
  -> If it funds BOTH students and researchers -> INCLUDE (dual-purpose is valid)
  -> If the purpose contains "grundutbildning" or "grundniva" -> ALWAYS INCLUDE for undergrad users

STUDY LEVEL EXCEPTION:
  If the user IS a researcher (PhD / postdoc / doctoral) -> also include research-primary scholarships.
  If the user is UNDERGRADUATE -> exclude scholarships that are EXCLUSIVELY doctoral/postdoc/teaching with NO student component.

===============================================
STEP 2 -- DOMAIN MATCH
===============================================
After subject+level matches, evaluate domain fit.

{domain_context}

===============================================
STEP 3 -- ENTITY TYPE CHECK
===============================================
EXCLUDE these regardless of subject:
  - Funds for professorships, guest professorships, chairs, lectureships (not student-facing)
  - Institutional support funds with no direct applicant pathway
  - Funds that support only faculty/department operations

INCLUDE these even if they mention research:
  - Student union funds (studentkar)
  - Direct scholarships/stipendier to named student groups
  - Generic university scholarships open to all students
  - Business school student funds
  - Research grants and forskarstipendier (for research users)

===============================================
STEP 4 -- DOUBT RULE
===============================================
DEFAULT ACTION IS INCLUDE. Only exclude when you are certain.

  -> Looks student-facing? -> ALWAYS INCLUDE for undergrad users
  -> Looks research-focused? -> ALWAYS INCLUDE for research users
  -> General university scholarship? -> INCLUDE, it may be relevant
  -> Missing explicit subject keyword but context suggests match? -> INCLUDE
  -> Clearly wrong domain (medicine for law user)? -> EXCLUDE
  -> Clearly institutional only (professor salary fund)? -> EXCLUDE

When uncertain: INCLUDE. The reranker will handle quality sorting afterward.
Return ONLY a JSON array -- no text, no markdown:
[{{"index": 0, "relevance": "relevant"}}, {{"index": 1, "relevance": "irrelevant"}}]"""

    scholarship_list = "\n".join([
        f"[{i}] {s['Name']}: {s['Purpose'][:400]}"
        for i, s in enumerate(scholarships)
    ])

    user_prompt = (
        f"Evaluate these scholarships for: \"{user_purpose}\"\n\n"
        f"Remember: User is {study_level_context}. "
        f"Check study level first, then domain.\n\n"
        f"Scholarships:\n{scholarship_list}\n\n"
        f"Minimum {min_results} relevant results required. "
        f"Return the JSON array now."
    )

    response = oai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        seed=42,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ]
    )

    try:
        raw         = response.choices[0].message.content.strip()
        start       = raw.index("[")
        end         = raw.rindex("]") + 1
        decisions   = json.loads(raw[start:end])
        rel_indices = {
            d["index"] for d in decisions
            if isinstance(d, dict) and d.get("relevance") == "relevant"
        }
        rel_indices = {i for i in rel_indices if 0 <= i < len(scholarships)}
        final_list  = [scholarships[i] for i in sorted(rel_indices)]

        if len(final_list) < min_results:
            if debug:
                print(f"\n[SAFETY NET] LLM returned {len(final_list)} — padding to {min_results}")

            included_names = {s["Name"] for s in final_list}

            domain_padding = [
                s for s in scholarships
                if s["Name"] not in included_names
                and is_domain_match(combined_scholarship_text(s), user_purpose)
            ]
            student_padding = [
                s for s in scholarships
                if s["Name"] not in included_names
                and s["Name"] not in {x["Name"] for x in domain_padding}
                and is_strongly_student_facing(combined_scholarship_text(s))
            ]
            remaining_padding = [
                s for s in scholarships
                if s["Name"] not in included_names
                and s["Name"] not in {x["Name"] for x in domain_padding}
                and s["Name"] not in {x["Name"] for x in student_padding}
            ]

            needed     = min_results - len(final_list)
            padding    = (domain_padding + student_padding + remaining_padding)[:needed]
            final_list = final_list + padding

            if debug:
                print(f"[SAFETY NET] Padded to {len(final_list)} results")

        if debug:
            excluded = [s for i, s in enumerate(scholarships) if i not in rel_indices]
            print(f"\n{'='*60}")
            print(f"[LLM FILTER] INCLUDED ({len(final_list)}):")
            print(f"{'='*60}")
            for s in final_list:
                cls    = classify_scholarship(s)
                is_dom = is_domain_match(combined_scholarship_text(s), user_purpose)
                group  = "GROUP A" if is_dom else "GROUP B"
                print(f"  [{group}][{cls:>8}] {s['Name']}")
                print(f"            Purpose: {s['Purpose'][:200]}")
                print(f"  {'-'*56}")
            print(f"\n{'='*60}")
            print(f"[LLM FILTER] EXCLUDED ({len(excluded)}):")
            print(f"{'='*60}")
            for s in excluded:
                cls = classify_scholarship(s)
                print(f"  [{cls:>8}] {s['Name']}")
                print(f"            Purpose: {s['Purpose'][:200]}")
                print(f"  {'-'*56}")

        return final_list

    except Exception as e:
        if debug:
            print(f"[LLM FILTER] FAILED: {e} — returning all candidates unchanged")
        return scholarships


def rerank_with_llm(query, scholarships, oai_client, top_n=10, debug=True, user_type=None, custom_rerank_prompt=None, gender=None):
    is_undergrad = contains_any(query, UNDERGRAD_TERMS)
    _is_res_user = is_research_user(query)
    user_domain  = get_user_domain(query)
    is_org_user  = user_type and user_type.lower() in ["organization", "organisation", "idrottsförening"]

    # Build gender_rule at top so all branches can access it
    gender_rule = ""
    # Handle both English and Swedish gender values
    gender_lower = gender.lower() if gender else ""
    if gender_lower in ["male", "man"]:
        gender_rule = "User is male. Exclude scholarships explicitly for women only."
    elif gender_lower in ["female", "kvinna", "woman"]:
        gender_rule = "User is female. Exclude scholarships explicitly for men only."

    gender_instruction = (
        f"GENDER RULE: {gender_rule}\n"
        f"Any scholarship with a gender restriction not matching the user "
        f"must be ranked absolutely last regardless of domain.\n\n"
    ) if gender_rule else ""

    domain_configs = {
        "law": {
            "label": "LAW",
            "swedish_label": "JURIDIK",
            "subject_terms": [
                "juridik", "juridisk", "jurist", "rättsvetenskap",
                "folkrätt", "affärsjuridik", "sjörätt", "EG-rätt",
                "juridiska fakulteten", "juristprogrammet"
            ]
        },
        "business": {
            "label": "BUSINESS",
            "swedish_label": "EKONOMI",
            "subject_terms": [
                "ekonomi", "företagsekonomi", "handelshögskolan",
                "civilekonom", "nationalekonomi", "handel",
                "marknadsföring", "redovisning", "finance",
                "handelsprogrammet", "ekonomistudent",
                "school of economics", "school of business",
                "business school", "SSE", "HHS", "bachelor students",
                "business students", "economics students"
            ]
        },
        "technology": {
            "label": "TECHNOLOGY",
            "swedish_label": "TEKNIK",
            "subject_terms": [
                "teknik", "teknisk", "ingenjör",
                "datateknik", "datavetenskap", "IT", "KTH",
                "Chalmers", "tekniska fakulteten", "software"
            ]
        },
        "medical": {
            "label": "MEDICAL",
            "swedish_label": "MEDICIN",
            "subject_terms": [
                "medicin", "medicinsk", "läkare", "sjukvård",
                "karolinska", "biomedicin", "klinisk",
                "läkarprogrammet", "farmaci", "tandläkare"
            ]
        }
    }

    cfg           = domain_configs.get(user_domain, None)
    domain_label  = cfg["label"]         if cfg else "GENERAL"
    swedish_label = cfg["swedish_label"] if cfg else "ämne"
    subject_terms = ", ".join(cfg["subject_terms"]) if cfg else ""

    formatted = "\n".join([
        f"{i+1}. {s['Name']}: {s['Purpose'][:200]}"
        for i, s in enumerate(scholarships)
    ])

    if is_org_user:
        org_tier_block = f"""

PRE-CHECK — APPLY BEFORE ASSIGNING ANY TIER

This is an ORGANISATION applicant (förening, klubb, juridisk person).
Before placing any scholarship in a tier, answer these two questions:

QUESTION 1 — Does the scholarship name an ORGANISATION as recipient?
  Look for ANY of these terms referring to the applicant or recipient:
    - förening, föreningar, idrottsförening, idrottsföreningar
    - klubb, klubbar, sportförening, sportföreningar
    - juridiska personer, juridisk person
    - organisationer, organisation, sammanslutning
    - verksamhetsstöd, verksamhetsbidrag, föreningsbidrag, föreningsstöd
    - utrustning (to a club or association, not an individual)
    - utrustningsbidrag, lägerbidrag, träningsläger
    - ungdomsverksamhet (when ORGANISATION runs the activity)
    - ideell förening, ideella föreningar
    - lag, enskilda lag (as a team/club entity, not individual player)
    - "stöd till föreningar", "bidrag till föreningar"
    - "för sin verksamhet", "för verksamheten"
  → If YES to any above → Tier 1 candidate. Go to Tier Assignment.

QUESTION 2 — Does the scholarship ONLY name INDIVIDUALS as recipients
             with NO organisational pathway at all?
  Individual-only signals (ONE or more is enough to confirm):
    - ungdomar / ungdom (youth as direct money recipients)
    - elev / elever (individual school students)
    - studerande / studenter (individual university students)
    - talanger / lovande talanger (individual talented persons)
    - en ung person / unga personer (specific individuals)
    - individuella sökande / enskilda sökande / enskilda idrottare
    - gymnast / spelare / idrottsutövare (individual athletes)
    - barn (individual children as direct recipients)
    - person / personer (when the ONLY recipient type named)

  AND confirm NO organisational pathway exists — NONE of these appear:
    - förening, klubb, organisation, sammanslutning
    - juridiska personer, juridisk person
    - verksamhetsstöd, föreningsbidrag, verksamhetsbidrag
    - utrustning, läger, lägerbidrag
    - "för sin verksamhet", "för verksamheten"

TIER ASSIGNMENT


TIER 1 — ORGANISATION DIRECT FUNDING (show first)

The scholarship explicitly names an organisation as applicant
or recipient, OR the purpose is clearly about funding organisational
activities rather than individuals.

Strong Tier 1 signals (one is enough to place here):
  - förening / idrottsförening / klubb named as eligible applicant
  - juridiska personer explicitly mentioned as eligible
  - verksamhetsstöd / verksamhetsbidrag / föreningsbidrag / föreningsstöd
  - utrustningsbidrag / utrustning till förening eller klubb
  - lägerbidrag / träningsläger (organisation arranges the camp)
  - ungdomsverksamhet where the förening or klubb is the applicant
  - ideell förening / ideella föreningar as the applicant type
  - "stöd till föreningar" / "bidrag till föreningar"
  - "för sin verksamhet" / "för verksamheten"
  - lag or enskilda lag as a team-level applicant (not individual player)
  - sammanslutning named as eligible recipient

Within Tier 1, rank HIGHER if:
  → Explicitly says "juridiska personer" or "förening kan söka"
  → Mentions multiple org-applicable activities (utrustning + läger)
  → Has no individual-only restriction anywhere in the purpose
  → Purpose matches the user's stated activity area closely

Within Tier 1, rank LOWER if:
  → Org eligibility is implied rather than explicit
  → Purpose mixes both org and individual recipients
  → Geographic restriction reduces fit


TIER 2 — BROAD SPORTS/ACTIVITY FUNDING (no individual lock)

Scholarships about idrott, sport, kultur, or ungdomsverksamhet
that do NOT explicitly restrict recipients to individuals only,
and where a förening or klubb could plausibly apply.
**If you see two sport is mentioned by user then try to give two sports scholarships**
Tier 2 signals:
  - idrott / sport / idrottsverksamhet without naming only individuals
  - "stöd till idrott" / "bidrag till idrott" without individual lock
  - Broad cultural or community activity funding
  - Purpose mentions both individuals AND associations as potential recipients
  - No explicit individual-only restriction found
  - Activity type matches user's purpose even if applicant type unclear

Within Tier 2, rank HIGHER if:
  → Activity area closely matches user's stated purpose
  → Purpose is genuinely ambiguous (could be org or individual)
  → Mentions any org-adjacent term loosely

Within Tier 2, rank LOWER if:
  → Leans more toward individual language but not confirmed
  → Activity area is only loosely related to user's purpose
  → Geographic restriction reduces fit
  → No mention of sport, idrott, or the user's specific activity area


TIER 3 — MIXED OR UNCLEAR APPLICANT TYPE

TIER 3 — MIXED OR UNCLEAR APPLICANT TYPE

Purpose is genuinely ambiguous. Cannot clearly confirm whether
an organisation OR individual is the intended applicant.
Not enough signals for Tier 1 or 2, but not clearly Tier 4 either.

Within Tier 3, rank HIGHER if:
  → Activity area matches the user's stated purpose (sport, kultur etc.)
  → Mentions any org-adjacent term loosely

Within Tier 3, rank LOWER if:
  → Activity area has no connection to user's stated purpose
  → Purpose is about a completely different field (environment, 
     sustainability, social causes) with no sport or activity link


TIER 4 — INDIVIDUAL RECIPIENTS ONLY (show last)

Only scholarships that passed ALL THREE pre-check conditions above:
  1. Two or more individual recipient signals confirmed
  2. Zero organisational pathway terms found
  3. Personal individual criteria required

Examples of clear Tier 4:
  - Youth scholarships going directly to ungdomar as individuals
  - Student scholarships requiring university enrollment
  - Individual athlete talent scholarships
  - School student prizes for personal academic merit
  - Scholarships requiring personal birth location or residency

FILL RULE AND OUTPUT ORDER

Always output in strict tier order: Tier 1 → Tier 2 → Tier 3 → Tier 4.
Never skip tiers. Never mix tiers in the output.

If fewer than 10 scholarships exist across Tier 1 and Tier 2:
  → Fill remaining slots from Tier 3 before touching Tier 4.
  → Only use Tier 4 entries if Tier 1 + 2 + 3 combined are fewer than 10.

If total pool has fewer than 10 scholarships:
  → Output all available, still in strict tier order.

IMPORTANT — DO NOT place a scholarship in Tier 1 or Tier 2 simply
because it supports sport or youth in a general sense.
The deciding factor is always: WHO receives the money?
If the money goes to an individual person → Tier 4.
If the money goes to an organisation or could go to one → Tier 1 or 2.
"""

        org_level_note = (
            f"USER CONTEXT: ORGANISATION (förening/klubb/juridisk person).\n"
            f"The applicant is an organisation, NOT an individual person.\n"
            f"Scholarships that only fund individual ungdomar, elever, or studerande\n"
            f"must go to Tier 4 unless they also mention förening, klubb, or juridiska personer.\n\n"
        )

        prompt = (
            f"Rank these scholarships for the organisation query: \"{query}\".\n\n"
            f"{org_level_note}"
            f"{org_tier_block}\n"
            f"STEP-BY-STEP BEFORE YOU RESPOND:\n"
            f"  Step 0 — Apply DISQUALIFICATION RULE first.\n"
            f"            Individual-only scholarships (ungdomar, elev, studerande)\n"
            f"            with no förening/klubb/juridiska personer mention → TIER 4.\n"
            f"  Step 1 — Identify Tier 1: explicit organisation funding.\n"
            f"            förening, juridiska personer, verksamhetsstöd, föreningsbidrag.\n"
            f"  Step 2 — Identify Tier 2: broad sports/activity funding an org could apply for.\n"
            f"  Step 3 — Identify Tier 3: ambiguous applicant type.\n"
            f"  Step 4 — All individual-only go to Tier 4 last.\n"
            f"  Step 5 — Verify no lower tier appears above a higher tier.\n\n"
            f"Return ONLY a JSON array of 1-based positions: [3, 1, 2, ...]\n\n"
            f"Scholarships:\n{formatted}"
        )

        system_content = (
            "You are a strict JSON-only scholarship ranker for an ORGANISATION applicant. "
            "The user is a förening, klubb, or juridisk person — NOT an individual. "
            "TIER 1: explicit organisation funding — förening, juridiska personer, verksamhetsstöd. "
            "TIER 2: broad sports or activity funding an organisation could apply for. "
            "TIER 3: mixed or unclear applicant type. "
            "TIER 4: individual-only scholarships — ungdomar, elev, studerande with no org pathway. "
            "Scholarships funding only individual persons go dead last. "
            "Never place a lower tier above a higher tier. "
            "Output only a valid JSON array of integers."
        )

  
    else:
        if is_undergrad:
            level_note = (
                f"USER CONTEXT: {domain_label} UNDERGRADUATE student.\n"
                f"Subject-specific direct personal scholarships must occupy positions 1 onwards.\n"
                f"Gymnasium scholarships and institutional research funds always go last.\n\n"
            )
            tier_block = f"""

AUTOMATIC DISQUALIFICATION — CHECK BEFORE ASSIGNING TIERS

These two rules override all tier placement.
Apply them first before reading the tier definitions below.

DISQUALIFICATION RULE 1 — WRONG EDUCATION LEVEL:
  If the scholarship explicitly targets any of the following, place it in TIER 4 regardless of any other signal:
- gymnasieelever, gymnasieskolan, gymnasiet
- elev vid school name or elev i school name when the school is a high school or gymnasium
- årskurs 1, årskurs 2, årskurs 3 when referring to gymnasium
- grundskolan, grundskoleelev
- any pre-university or high school level student
  A gymnasium scholarship is never relevant for a
  university undergraduate student. Even if it mentions
  the user's subject area, place it in Tier 4.

DISQUALIFICATION RULE 2 — INSTITUTIONAL NOT PERSONAL:
  If the scholarship primarily funds research infrastructure,
  a research foundation, or academic institution operations
  AND does not describe a direct personal application pathway
  for individual students, place it in TIER 4.
  A domain term match alone does NOT make it Tier 1.

  Signals that confirm it is INSTITUTIONAL (→ Tier 4):
    - "stödja forskning", "vetenskaplig forskning" as primary purpose
    - "institutionen för", "forskningsverksamhet"
    - "jubileumsfond" funding research rather than student stipendier
    - No mention of individual application, ansökan, or sökande
    - No explicit amount per student or number of recipients
    - Supports the institution itself, not the students at it

  Example: A fund named after a business school that supports
  research at that school is NOT a scholarship for business students.
  It belongs in Tier 4.
TIER 1 — {domain_label}-SPECIFIC DIRECT SCHOLARSHIPS
Place these in positions 1 onwards. Fill as many as possible here.

A scholarship belongs in Tier 1 if it meets BOTH conditions:

CONDITION A — Subject match (Swedish OR English terms count equally):
  Contains any of: {subject_terms}
  OR targets students at a {domain_label.lower()} faculty or program
  OR uses English institution names that are well-known business/law/
  technology/medical schools in Sweden

  CRITICAL: English-language scholarships qualify fully.
  "Bachelor students at SSE", "Stockholm School of Economics",
  "School of Economics", "faculty of law", "engineering students"
  are all valid Tier 1 subject signals. Do NOT require Swedish
  keywords to confirm a subject match. Read the meaning, not just
  the language.

CONDITION B — Direct personal scholarship (not institutional):
  Describes a scholarship that individual students apply to directly.
  At least one of these must be present:
    - Explicit amount per recipient (e.g. SEK 50,000 each)
    - Number of recipients (e.g. seven scholarships)
    - Application language: ansökan, sökande, apply, applications
    - Named student group receiving the scholarship
  A fund that "supports research" or "contributes to" an institution
  does NOT meet Condition B even if the institution is relevant.

TIER 2 — STUDY LEVEL MATCHED SCHOLARSHIPS

Place these after all Tier 1 scholarships.

A scholarship belongs here if:
  - No subject restriction — open to any university field
  - Explicitly targets the user's study level
    (kandidat, bachelor, undergraduate, master, doktorand)
  - Individual students can apply directly
  - Is NOT gymnasium or pre-university level

TIER 3 — GENERIC OPEN-TO-ALL SCHOLARSHIPS

Place these after all Tier 2 scholarships.

A scholarship belongs here if:
  - No subject restriction
  - No explicit study level restriction
  - Any university student can apply
  - General merit, need-based, or geographic scholarships
  - Individual students can apply directly

TIER 4 — DEAD LAST (research, institutional, wrong level)

Place these last. Everything disqualified above also goes here.

A scholarship belongs here if ANY of these are true:
  - Gymnasium or pre-university level (Rule 1 above)
  - Primarily funds research or institution operations (Rule 2 above)
  - Mixed purpose with no clear individual student pathway
  - Primarily research or travel grants for researchers
  - Eligibility is unclear or requires assumptions to confirm
  A scholarship targeting pre-university students is never relevant for a university undergraduate user. Even if it mentions the user's subject area

FILL RULE:
  If fewer than {top_n} Tier 1 scholarships exist, fill remaining
  slots with Tier 2 first, then Tier 3, then Tier 4.
  Always in strict order. Never skip tiers to pad results.
"""
            system_content = (
                "You are a strict JSON-only scholarship ranker for an UNDERGRADUATE student. "
                f"Ranking for a {domain_label} undergraduate user. "
                "Apply disqualification first: gymnasium → Tier 4, institutional research → Tier 4. "
                "TIER 1: subject-specific direct personal scholarships, English names qualify. "
                "TIER 2: study level matched open-to-all scholarships. "
                "TIER 3: generic open-to-all university scholarships. "
                "TIER 4: research, institutional, gymnasium — always last. "
                "Output only a valid JSON array of integers."
            )
            step_checklist = (
                f"  Step 0 — Gymnasium → Tier 4. Institutional research → Tier 4.\n"
                f"  Step 1 — Tier 1: subject match AND direct personal scholarship.\n"
                f"            English names like SSE, Bachelor students qualify.\n"
                f"  Step 2 — Tier 2: study level matched, any subject. After Tier 1.\n"
                f"  Step 3 — Tier 3: generic open-to-all. After Tier 2.\n"
                f"  Step 4 — Tier 4: all remaining last.\n"
                f"  Step 5 — No lower tier above higher tier.\n"
            )



        else:
            level_note = (
                f"USER CONTEXT: {domain_label} student (level not specified).\n"
                f"Rank subject-specific direct scholarships first.\n\n"
            )
            tier_block = f"""
AUTOMATIC DISQUALIFICATION — CHECK BEFORE ASSIGNING TIERS

DISQUALIFICATION RULE — INSTITUTIONAL NOT PERSONAL:
  If the scholarship primarily funds research infrastructure,
  institutional operations, or academic department activities
  AND does not describe a direct personal application pathway,
  place it in TIER 3 (dead last).

  Signals that confirm INSTITUTIONAL (→ Tier 3):
    - "att skapa en institution", "institutionens verksamhet"
    - "främja forskning" or "stödja forskning" as the SOLE purpose
    - "jubileumsfond" funding research rather than student stipendier
    - No mention of ansökan, sökande, or individual application
    - No explicit amount per recipient or number of recipients
  A domain term match alone does NOT save it from Tier 3.

TIER 1 — {domain_label}-SPECIFIC DIRECT SCHOLARSHIPS:
  Contains any of: {subject_terms}
  Direct scholarship individual students apply to.
  Must have: stipendium, bidrag, ansökan, or explicit recipient info.

TIER 2 — GENERAL UNIVERSITY SCHOLARSHIPS:
  No subject restriction, open to any university student.

TIER 3 — MIXED, UNCLEAR, OR INSTITUTIONAL:
  Institutional funds, research foundations, unclear pathway.

FILL RULE: Tier 1 first, Tier 2, Tier 3 last.
"""
            system_content = (
                "You are a strict JSON-only scholarship ranker. "
                f"TIER 1: subject-specific direct scholarships for {domain_label}. "
                "TIER 2: general university scholarships. "
                "TIER 3: mixed or unclear. "
                "Output only a valid JSON array of integers."
            )
            step_checklist = (
                f"  Step 1 — Tier 1: subject-specific direct scholarships. Place first.\n"
                f"  Step 2 — Tier 2: general university scholarships. After Tier 1.\n"
                f"  Step 3 — Tier 3: all remaining last.\n"
            )

        gender_instruction = (
            f"GENDER RULE: {gender_rule.strip()}\n"
            f"Any scholarship with a gender restriction not matching the user "
            f"must be ranked absolutely last regardless of domain.\n\n"
        ) if gender_rule else ""
        prompt = (
            f"Rank these scholarships for the user query: \"{query}\".\n\n"
            f"{gender_instruction}"
            f"{level_note}"
            f"{tier_block}\n"
            f"STEP-BY-STEP BEFORE YOU RESPOND:\n"
            f"{step_checklist}\n"
            f"Return ONLY a JSON array of 1-based positions: [3, 1, 2, ...]\n\n"
            f"Scholarships:\n{formatted}"
        )


  
    if custom_rerank_prompt:
        system_content = custom_rerank_prompt

    response = oai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        seed=42,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user",   "content": prompt}
        ]
    )

    raw = response.choices[0].message.content.strip()
    try:
        start    = raw.index("[")
        end      = raw.rindex("]") + 1
        idx_list = json.loads(raw[start:end])
        ranked   = [scholarships[i - 1] for i in idx_list if 1 <= i <= len(scholarships)]

        if debug:
            print(f"\n{'='*60}")
            print(f"[LLM RERANK] Final Order (top {top_n}):")
            print(f"{'='*60}")
            for i, s in enumerate(ranked[:top_n]):
                cls    = classify_scholarship(s)
                is_dom = is_domain_match(combined_scholarship_text(s), query)
                tier   = "TIER 1" if is_dom else "TIER 2+"
                print(f"  {i+1}. [{tier}][{cls:>8}] {s['Name']}")
                print(f"     Purpose: {s['Purpose'][:200]}")
                print(f"  {'-'*56}")

        return ranked[:top_n]

    except Exception as e:
        if debug:
            print(f"[LLM RERANK] FAILED: {e}")
        return scholarships[:top_n]




# def find_scholarships_v2(
#     user_purpose,
#     gender=None,
#     top_k=DEFAULT_TOP_K,
#     debug=True,
#     use_llm_rerank=True,
#     user_type=None,
#     municipality_filter=False,
#     municipality=None,
#     custom_system_prompt=None,
#     custom_rerank_prompt=None,
# ):
#     global index, INDEX_NAME
    
  
#     try:
#         from django.conf import settings
#         if settings.SITE_CONFIG:
#             INDEX_NAME = settings.SITE_CONFIG.get_active_dataset_index_name()
#             index = pc.Index(INDEX_NAME)
#     except Exception as e:
#         if debug:
#             print(f"Note: Using default index. Details: {e}")
    
#     _is_res_user = is_research_user(user_purpose)
#     _is_ug_user = contains_any(user_purpose, UNDERGRAD_TERMS)
 
#     if debug:
#         print(f"\n{'#'*60}")
#         print(f"# SEARCH: {user_purpose}")
#         print(f"# Domain: {get_user_domain(user_purpose)}")
#         print(f"# Undergrad: {_is_ug_user}")
#         print(f"# Research User: {_is_res_user}")
#         print(f"# Top-K: {top_k}")
#         print(f"# User Type: {user_type or 'not specified'}")
#         print(f"# Municipality Filter: {municipality_filter} | Municipality: {municipality or 'none'}")
#         print(f"{'#'*60}")
 
#     filters = {}
 
#     if user_type:
#         user_type_lower = user_type.lower()
#         if user_type_lower in ["individual", "privatperson", "person"]:
#             filters["Kommentar"] = {"$in": ["Flera", "Studier"]}
#         elif user_type_lower in ["organization", "organisation", "idrottsförening"]:
#             filters["Kommentar"] = {"$in": ["Flera", "Idrottsförening"]}
 
#     # if municipality_filter and municipality:
#     #     filters["Kommun"] = municipality.strip()
#     if municipality_filter and municipality:
#         filters["Kommun"] = resolve_municipality(municipality)
#     if debug:
#         print(f"Pinecone Filters:\n{json.dumps(filters, indent=4, ensure_ascii=False)}\n")
 
#     emb_query = expand_user_query_for_embedding(user_purpose)
#     query_vector = openai_client.embeddings.create(
#         model=EMBEDDING_MODEL, input=emb_query
#     ).data[0].embedding
 
    
#     if filters:
#         res = index.query(vector=query_vector, top_k=top_k, include_metadata=True, filter=filters)
#     else:
#         res = index.query(vector=query_vector, top_k=top_k, include_metadata=True)
 
#     initial_list = []
#     for m in res.get("matches", []):
#         md = m["metadata"]
#         s = {
#             "Name": md.get("Namn", ""),
#             "Purpose": md.get("Ändamål", ""),
#             "Study Level": md.get("Utbildningsnivå", ""),
#             "Base Score": round(m["score"], 4)
#         }
#         for k, v in FIELD_MAP_SV.items():
#             if k not in s:
#                 s[k] = md.get(v, "")
#         s["Relevance Score"] = compute_soft_score(s, user_purpose)
#         s["Entity Bonus"] = compute_entity_bonus(s, user_purpose)
#         s["Adjusted Score"] = round(
#             s["Base Score"] + s["Relevance Score"] + s["Entity Bonus"], 4
#         )
#         initial_list.append(s)
 
#     if debug:
#         print(f"\n{'='*60}")
#         print(f"[PINECONE] Retrieved {len(initial_list)} candidates")
#         print(f"{'='*60}")

#     kept_rules = []
#     excluded_rules = []
 
#     for sch in initial_list:
#         # Gender check runs first — cheapest, most reliable, domain-agnostic
#         if gender:
#             fail_gender, gender_reason = should_exclude_gender_mismatch(sch, gender)
#             if fail_gender:
#                 excluded_rules.append((sch, gender_reason))
#                 continue

#         fail_entity, entity_reason = should_exclude_entity_type(sch, user_purpose)
#         if fail_entity:
#             excluded_rules.append((sch, entity_reason))
#             continue

#         fail_research, research_reason = should_exclude_research_doctoral(sch, user_purpose)
#         if fail_research:
#             cls = classify_scholarship(sch)
#             excluded_rules.append((sch, f"Research Mismatch [{cls}] - {research_reason}"))
#             continue

#         fail_level, level_reason = should_exclude_study_level_mismatch(sch, user_purpose)
#         if fail_level:
#             excluded_rules.append((sch, f"Study Level Mismatch - {level_reason}"))
#             continue

#         kept_rules.append(sch)
 
#     if debug:
#         pass  
#     kept_semantic = []
#     excluded_semantic = []
 
#     for sch in kept_rules:
#         if semantic_prefilter(sch, user_purpose):
#             kept_semantic.append(sch)
#         else:
#             excluded_semantic.append(sch)
 
#     if debug:
#         pass  
#     final_data = sorted(
#         kept_semantic, key=lambda x: x["Adjusted Score"], reverse=True
#     )[:MAX_CANDIDATES_FOR_LLM]
 
#     if debug:
#         print(f"\n{'='*60}")
#         print(f"[PRE-LLM] Sending {len(final_data)} candidates to LLM filter")
#         print(f"{'='*60}")
 
  
#     if final_data:
#         llm_filtered = llm_filter_scholarships(
#             user_purpose, gender, final_data, openai_client, debug=debug, custom_system_prompt=custom_system_prompt, user_type=user_type
#         )
#         if len(llm_filtered) < MIN_RESULTS:
#             if debug:
#                 print(f"\n[SAFETY NET] LLM returned only {len(llm_filtered)} -- padding to {MIN_RESULTS}")
#             existing_names = {s["Name"] for s in llm_filtered}
#             padding = [s for s in final_data if s["Name"] not in existing_names]
#             final_data = llm_filtered + padding[:MIN_RESULTS - len(llm_filtered)]
#         else:
#             final_data = llm_filtered
 
#     if use_llm_rerank and len(final_data) > 1:
#         final_data = rerank_with_llm(
#             user_purpose, final_data, openai_client, debug=debug, custom_rerank_prompt=custom_rerank_prompt, user_type=user_type, gender=gender
#         )
 
#     if debug:
#         print(f"\n{'='*60}")
#         print(f"[FINAL] Returning {len(final_data[:MIN_RESULTS])} results")
#         print(f"{'='*60}")
#         for i, s in enumerate(final_data[:MIN_RESULTS]):
#             cls = classify_scholarship(s)
#             print(f"  {i+1}. [{cls:>8}] {s['Name']}")
#             print(f"     Purpose: {s['Purpose'][:200]}")
 
#     return final_data[:MIN_RESULTS]

def find_scholarships_v2(
    user_purpose,
    gender=None,
    top_k=DEFAULT_TOP_K,
    debug=True,
    use_llm_rerank=True,
    user_type=None,
    municipality_filter=False,
    municipality=None,
    custom_system_prompt=None,
    custom_rerank_prompt=None,
):
    global index, INDEX_NAME

    try:
        from django.conf import settings
        if settings.SITE_CONFIG:
            INDEX_NAME = settings.SITE_CONFIG.get_active_dataset_index_name()
            index = pc.Index(INDEX_NAME)
    except Exception as e:
        if debug:
            print(f"Note: Using default index. Details: {e}")

    _is_res_user = is_research_user(user_purpose)
    _is_ug_user = contains_any(user_purpose, UNDERGRAD_TERMS)
    is_org_user = user_type and user_type.lower() in ["organization", "organisation", "idrottsförening"]

    if debug:
        print(f"\n{'#'*60}")
        print(f"# SEARCH: {user_purpose}")
        print(f"# Domain: {get_user_domain(user_purpose)}")
        print(f"# Undergrad: {_is_ug_user}")
        print(f"# Research User: {_is_res_user}")
        print(f"# Top-K: {top_k}")
        print(f"# User Type: {user_type or 'not specified'}")
        print(f"# Municipality Filter: {municipality_filter} | Municipality: {municipality or 'none'}")
        print(f"{'#'*60}")

    # Base filters (user_type only — no municipality yet)
    base_filters = {}
    if user_type:
        user_type_lower = user_type.lower()
        if user_type_lower in ["individual", "privatperson", "person"]:
            base_filters["Kommentar"] = {"$in": ["Flera", "Studier"]}
        elif user_type_lower in ["organization", "organisation", "idrottsförening"]:
            base_filters["Kommentar"] = {"$in": ["Flera", "Idrottsförening"]}

    if debug:
        print(f"Base Filters:\n{json.dumps(base_filters, indent=4, ensure_ascii=False)}\n")

    emb_query = expand_user_query_for_embedding(user_purpose)
    query_vector = openai_client.embeddings.create(
        model=EMBEDDING_MODEL, input=emb_query
    ).data[0].embedding

    # -------------------------------------------------------
    # RETRIEVAL — two paths depending on org + municipality
    # -------------------------------------------------------
    if is_org_user and municipality_filter and municipality:
        resolved_municipality = resolve_municipality(municipality)

        if debug:
            print(f"[ORG SOFT GEOGRAPHY] Municipality: {municipality} → {resolved_municipality}")
            print(f"[ORG SOFT GEOGRAPHY] Fetching local pool + national pool separately")

        # POOL 1 — Local: municipality match + org filter
        local_filters = dict(base_filters)
        local_filters["Kommun"] = resolved_municipality

        local_res = index.query(
            vector=query_vector,
            top_k=50,
            include_metadata=True,
            filter=local_filters
        )

        # POOL 2 — National: org filter only, no municipality restriction
        national_res = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=base_filters if base_filters else None
        )

        if debug:
            print(f"[ORG SOFT GEOGRAPHY] Local results: {len(local_res.get('matches', []))}")
            print(f"[ORG SOFT GEOGRAPHY] National results: {len(national_res.get('matches', []))}")

        # Merge: local first then national, deduplicate by name
        seen_names = set()
        merged_matches = []

        for m in local_res.get("matches", []):
            name = m["metadata"].get("Namn", "")
            if name not in seen_names:
                m["_is_local"] = True
                merged_matches.append(m)
                seen_names.add(name)

        for m in national_res.get("matches", []):
            name = m["metadata"].get("Namn", "")
            if name not in seen_names:
                m["_is_local"] = False
                merged_matches.append(m)
                seen_names.add(name)

        if debug:
            print(f"[ORG SOFT GEOGRAPHY] Merged pool: {len(merged_matches)} total")

        res = {"matches": merged_matches}

    else:
        # Original single-query path — individual users and org without municipality
        filters = dict(base_filters)
        if municipality_filter and municipality:
            filters["Kommun"] = resolve_municipality(municipality)

        if debug:
            print(f"Pinecone Filters:\n{json.dumps(filters, indent=4, ensure_ascii=False)}\n")

        if filters:
            res = index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter=filters
            )
        else:
            res = index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )

    # -------------------------------------------------------
    # Build initial list from matches
    # -------------------------------------------------------
    initial_list = []
    for m in res.get("matches", []):
        md = m["metadata"]
        s = {
            "Name": md.get("Namn", ""),
            "Purpose": md.get("Ändamål", ""),
            "Study Level": md.get("Utbildningsnivå", ""),
            "Base Score": round(m["score"], 4),
            "_is_local": m.get("_is_local", False),
        }
        for k, v in FIELD_MAP_SV.items():
            if k not in s:
                s[k] = md.get(v, "")
        s["Relevance Score"] = compute_soft_score(s, user_purpose)
        s["Entity Bonus"] = compute_entity_bonus(s, user_purpose)
        s["Adjusted Score"] = round(
            s["Base Score"] + s["Relevance Score"] + s["Entity Bonus"], 4
        )
        initial_list.append(s)

    if debug:
        print(f"\n{'='*60}")
        print(f"[PINECONE] Retrieved {len(initial_list)} candidates")
        local_count = sum(1 for s in initial_list if s.get("_is_local"))
        if is_org_user and municipality_filter and municipality:
            print(f"[PINECONE] Local: {local_count} | National: {len(initial_list) - local_count}")
        print(f"{'='*60}")

    # -------------------------------------------------------
    # PASS 1 — Rules-based filtering
    # -------------------------------------------------------
    kept_rules = []
    excluded_rules = []

    for sch in initial_list:
        # Gender check runs first — cheapest, most reliable, domain-agnostic
        if gender:
            fail_gender, gender_reason = should_exclude_gender_mismatch(sch, gender)
            if fail_gender:
                excluded_rules.append((sch, gender_reason))
                continue

        fail_entity, entity_reason = should_exclude_entity_type(sch, user_purpose)
        if fail_entity:
            excluded_rules.append((sch, entity_reason))
            continue

        fail_research, research_reason = should_exclude_research_doctoral(sch, user_purpose)
        if fail_research:
            cls = classify_scholarship(sch)
            excluded_rules.append((sch, f"Research Mismatch [{cls}] - {research_reason}"))
            continue

        fail_level, level_reason = should_exclude_study_level_mismatch(sch, user_purpose)
        if fail_level:
            excluded_rules.append((sch, f"Study Level Mismatch - {level_reason}"))
            continue

        kept_rules.append(sch)

    if debug:
        print(f"\n{'='*60}")
        print(f"[RULE PASS] INCLUDED ({len(kept_rules)}) | EXCLUDED ({len(excluded_rules)})")
        print(f"{'='*60}")
        for s in kept_rules:
            cls = classify_scholarship(s)
            dm = "[DOMAIN]" if is_domain_match(combined_scholarship_text(s), user_purpose) else "[GENERAL]"
            local_tag = "[LOCAL]" if s.get("_is_local") else "[NATIONAL]"
            print(f"  [+] {local_tag}{dm}[{cls:>8}] {s['Name']}")
            print(f"      Purpose: {s['Purpose'][:150]}")
        print(f"\n  --- EXCLUDED ---")
        for s, reason in excluded_rules:
            print(f"  [-] {s['Name']} -> {reason}")

    # -------------------------------------------------------
    # PASS 2 — Semantic threshold
    # -------------------------------------------------------
    kept_semantic = []
    excluded_semantic = []

    for sch in kept_rules:
        if semantic_prefilter(sch, user_purpose):
            kept_semantic.append(sch)
        else:
            excluded_semantic.append(sch)

    if debug:
        print(f"\n{'='*60}")
        print(f"[SEMANTIC PASS] INCLUDED ({len(kept_semantic)}) | EXCLUDED ({len(excluded_semantic)})")
        print(f"{'='*60}")

    # For org soft geography: sort local before national within same score band
    # For everyone else: sort by adjusted score descending
    if is_org_user and municipality_filter and municipality:
        final_data = sorted(
            kept_semantic,
            key=lambda x: (not x.get("_is_local", False), -x["Adjusted Score"])
        )[:MAX_CANDIDATES_FOR_LLM]
    else:
        final_data = sorted(
            kept_semantic,
            key=lambda x: x["Adjusted Score"],
            reverse=True
        )[:MAX_CANDIDATES_FOR_LLM]

    if debug:
        print(f"\n{'='*60}")
        print(f"[PRE-LLM] Sending {len(final_data)} candidates to LLM filter")
        print(f"{'='*60}")

    # -------------------------------------------------------
    # PASS 3 — LLM filtering
    # -------------------------------------------------------
    if final_data:
        llm_filtered = llm_filter_scholarships(
            user_purpose, gender, final_data, openai_client,
            debug=debug,
            custom_system_prompt=custom_system_prompt,
            user_type=user_type
        )

        if len(llm_filtered) < MIN_RESULTS:
            if debug:
                print(f"\n[SAFETY NET] LLM returned only {len(llm_filtered)} — padding to {MIN_RESULTS}")

            existing_names = {s["Name"] for s in llm_filtered}

            # For org soft geography: prioritise local padding first
            if is_org_user and municipality_filter and municipality:
                local_padding = [
                    s for s in final_data
                    if s["Name"] not in existing_names
                    and s.get("_is_local", False)
                ]
                national_padding = [
                    s for s in final_data
                    if s["Name"] not in existing_names
                    and not s.get("_is_local", False)
                ]
                padding = (local_padding + national_padding)[:MIN_RESULTS - len(llm_filtered)]
            else:
                domain_padding = [
                    s for s in final_data
                    if s["Name"] not in existing_names
                    and is_domain_match(combined_scholarship_text(s), user_purpose)
                ]
                student_padding = [
                    s for s in final_data
                    if s["Name"] not in existing_names
                    and s["Name"] not in {x["Name"] for x in domain_padding}
                    and is_strongly_student_facing(combined_scholarship_text(s))
                ]
                remaining_padding = [
                    s for s in final_data
                    if s["Name"] not in existing_names
                    and s["Name"] not in {x["Name"] for x in domain_padding}
                    and s["Name"] not in {x["Name"] for x in student_padding}
                ]
                padding = (domain_padding + student_padding + remaining_padding)[:MIN_RESULTS - len(llm_filtered)]

            final_data = llm_filtered + padding

            if debug:
                print(f"[SAFETY NET] Padded to {len(final_data)} results")
        else:
            final_data = llm_filtered

    # -------------------------------------------------------
    # PASS 4 — LLM reranking
    # -------------------------------------------------------
    if use_llm_rerank and len(final_data) > 1:
        if debug:
            print(f"\n[LLM RERANK] Received {len(final_data)} scholarships to rank")

        final_data = rerank_with_llm(
            user_purpose, final_data, openai_client,
            debug=debug,
            custom_rerank_prompt=custom_rerank_prompt,
            user_type=user_type,
            gender=gender
        )

    if debug:
        print(f"\n{'='*60}")
        print(f"[FINAL] Returning {len(final_data[:MIN_RESULTS])} results")
        print(f"{'='*60}")
        for i, s in enumerate(final_data[:MIN_RESULTS]):
            cls = classify_scholarship(s)
            local_tag = "[LOCAL]" if s.get("_is_local") else "[NATIONAL]"
            print(f"  {i+1}. {local_tag}[{cls:>8}] {s['Name']}")
            print(f"     Purpose: {s['Purpose'][:200]}")

    return final_data[:MIN_RESULTS]

def run_single_audit(query: str, gender: str = None, debug: bool = False) -> Dict:
    results = find_scholarships_v2(query, gender=gender, debug=debug)
    audit = {
        "query": query,
        "gender": gender,
        "result_count": len(results),
        "results": []
    }
    for i, s in enumerate(results):
        text = combined_scholarship_text(s)
        cls = classify_scholarship(s)
        audit["results"].append({
            "rank": i + 1,
            "name": s.get("Name", ""),
            "purpose": s.get("Purpose", "")[:200],
            "base_score": s.get("Base Score", 0),
            "adjusted_score": s.get("Adjusted Score", 0),
            "classification": cls,
            "is_domain_specific": is_domain_match(text, query),
            "study_level": s.get("Study Level", ""),
        })
    return audit


def run_subject_audit(subject_label: str, query: str, gender: str = None, debug: bool = False):
    print(f"\n{'#'*70}")
    print(f"# AUDIT: {subject_label}")
    print(f"# Query: {query}")
    print(f"{'#'*70}")

    audit = run_single_audit(query, gender=gender, debug=debug)

    domain_count = sum(1 for r in audit["results"] if r["is_domain_specific"])
    student_count = sum(1 for r in audit["results"] if r["classification"] == "student")
    research_count = sum(1 for r in audit["results"] if r["classification"] == "research")
    mixed_count = sum(1 for r in audit["results"] if r["classification"] == "mixed")

    print(f"\nResults: {audit['result_count']} total")
    print(f"   Domain-specific: {domain_count}")
    print(f"   Student-facing: {student_count}")
    print(f"   Mixed: {mixed_count}")
    print(f"   Research-only: {research_count}")
    print()

    for r in audit["results"]:
        tag = "[DOMAIN]" if r["is_domain_specific"] else "[GENERAL]"
        cls_map = {
            "student": "[STUDENT]",
            "research": "[RESEARCH]",
            "mixed": "[MIXED]",
            "neutral": "[NEUTRAL]"
        }
        cls_tag = cls_map.get(r["classification"], "[NEUTRAL]")
        print(f"  {r['rank']:>2}. {tag}{cls_tag} [{r['adjusted_score']:.4f}] {r['name']}")
        print(f"      Level: {r['study_level']} | Class: {r['classification']}")
        print(f"      Purpose: {r['purpose']}")
        print()

    quality = min(100, int(
        (domain_count / max(audit["result_count"], 1)) * 30 +
        (student_count / max(audit["result_count"], 1)) * 30 +
        (mixed_count / max(audit["result_count"], 1)) * 10 +
        (40 if domain_count >= 1 and audit["results"][0].get("is_domain_specific") else 15) +
        (-20 * research_count / max(audit["result_count"], 1))
    ))
    print(f"  Estimated Quality Score: {quality}/100")
    audit["quality_score"] = quality
    return audit


def run_full_audit(queries: Dict[str, Dict] = None, debug: bool = False) -> Dict:
    if queries is None:
        queries = {
            "Technology": {"query": "Technology undergraduate scholarships in Sweden", "gender": None},
            "Business": {"query": "Business undergraduate scholarships in Sweden", "gender": None},
            "Law": {"query": "Law undergraduate scholarships in Sweden", "gender": None},
            "Medical": {"query": "Medical undergraduate scholarships in Sweden", "gender": None},
        }

    all_audits = {}
    for subject, params in queries.items():
        audit = run_subject_audit(
            subject, params["query"], params.get("gender"), debug=debug
        )
        all_audits[subject] = audit

    print(f"\n{'='*70}")
    print(f"  FULL AUDIT SUMMARY")
    print(f"{'='*70}")
    for subject, audit in all_audits.items():
        domain_count = sum(1 for r in audit["results"] if r["is_domain_specific"])
        student_count = sum(1 for r in audit["results"] if r["classification"] == "student")
        research_count = sum(1 for r in audit["results"] if r["classification"] == "research")
        mixed_count = sum(1 for r in audit["results"] if r["classification"] == "mixed")
        print(f"\n  {subject} -- Quality: {audit.get('quality_score', '?')}/100")
        print(f"     Domain: {domain_count} | Student: {student_count} | "
              f"Mixed: {mixed_count} | Research: {research_count}")
        for r in audit["results"]:
            tag = "[DOMAIN]" if r["is_domain_specific"] else "[GENERAL]"
            cls_map = {
                "student": "[STUDENT]",
                "research": "[RESEARCH]",
                "mixed": "[MIXED]",
                "neutral": "[NEUTRAL]"
            }
            cls_tag = cls_map.get(r["classification"], "[NEUTRAL]")
            print(f"     {r['rank']:>2}. {tag}{cls_tag} {r['name']}")
            print(f"         Purpose: {r['purpose']}")
    print(f"\n{'='*70}")
    return all_audits


def compare_audits(before: Dict, after: Dict):
    print(f"\n{'='*70}")
    print(f"  BEFORE / AFTER COMPARISON")
    print(f"{'='*70}")
    for subject in sorted(set(list(before.keys()) + list(after.keys()))):
        b = before.get(subject, {"results": [], "result_count": 0, "quality_score": 0})
        a = after.get(subject, {"results": [], "result_count": 0, "quality_score": 0})
        b_names = [r["name"] for r in b["results"]]
        a_names = [r["name"] for r in a["results"]]
        added = [n for n in a_names if n not in b_names]
        removed = [n for n in b_names if n not in a_names]
        kept = [n for n in a_names if n in b_names]

        print(f"\n  {subject}")
        print(f"     Quality: {b.get('quality_score', '?')}/100 -> {a.get('quality_score', '?')}/100")
        print(f"     Kept: {len(kept)} | Added: {len(added)} | Removed: {len(removed)}")
        if added:
            for n in added:
                print(f"       [+] {n}")
        if removed:
            for n in removed:
                print(f"       [-] {n}")
        if kept:
            changes = False
            for name in kept:
                b_rank = next((r["rank"] for r in b["results"] if r["name"] == name), "?")
                a_rank = next((r["rank"] for r in a["results"] if r["name"] == name), "?")
                if b_rank != a_rank:
                    if not changes:
                        print(f"     Rank Changes:")
                        changes = True
                    direction = "[UP]" if a_rank < b_rank else "[DOWN]"
                    print(f"       {direction} {name}: #{b_rank} -> #{a_rank}")
    print(f"\n{'='*70}")



# def format_scholarship_json(scholarship_list, output_language="en"):
#     formatted_list = []
#     non_translatable = {
#         "Email", "Website", "Phone", "Postal Code",
#         "Epost", "Websida", "Telefon", "Postnr",
#         "Municipality", "Kommun",
#         "City", "Stad",
#         "County", "Län",
#         "Main Address", "Huvudadress",
#     }
#     for sch in scholarship_list:
#         entry = {}
#         for k, v in sch.items():
#             if k in ["Base Score", "Relevance Score", "Entity Bonus", "Adjusted Score"]:
#                 continue
#             final_k = FIELD_MAP_SV.get(k, k) if output_language.lower() == "sv" else k
#             if k in non_translatable or not isinstance(v, str):
#                 entry[final_k] = v
#             else:
#                 entry[final_k] = (
#                     safe_translate(v, "sv", "en")
#                     if output_language.lower() == "en"
#                     else v
#                 )
#         formatted_list.append(entry)
#     return formatted_list
    #return json.dumps(formatted_list, indent=4, ensure_ascii=False)
def format_scholarship_json(scholarship_list, output_language="en"):
    formatted_list = []
    non_translatable = {
        "Email", "Website", "Phone", "Postal Code",
        "Epost", "Websida", "Telefon", "Postnr",
        "Municipality", "Kommun",
        "City", "Stad",
        "County", "Län",
        "Main Address", "Huvudadress",
    }
    for sch in scholarship_list:
        entry = {}
        for k, v in sch.items():
            if k in ["Base Score", "Relevance Score", "Entity Bonus", "Adjusted Score"]:
                continue
            
            # Always render Assets as integer — DB stores as float e.g. 7235778.0
            if k in ("Assets", "Tillgångar"):
                try:
                    entry[FIELD_MAP_SV.get(k, k) if output_language.lower() == "sv" else k] = int(float(v)) if v else v
                except (ValueError, TypeError):
                    entry[FIELD_MAP_SV.get(k, k) if output_language.lower() == "sv" else k] = v
                continue
            
            final_k = FIELD_MAP_SV.get(k, k) if output_language.lower() == "sv" else k
            if k in non_translatable or not isinstance(v, str):
                entry[final_k] = v
            else:
                entry[final_k] = (
                    safe_translate(v, "sv", "en")
                    if output_language.lower() == "en"
                    else v
                )
        formatted_list.append(entry)
    return formatted_list


def get_predefined_scholarships_by_level(predefined_queryset, study_level=None, subject=None, role=None, sport=None, debug=False):
    """
    Intelligently filters predefined scholarships based on study level for individuals.
    
    Hierarchy for INDIVIDUALS:
      1. Scholarships with subject='always' (filtered by study_level field)
      2. Then subject-specific scholarships (filtered by study_level field)
      3. Then AI-matched scholarships
    
    For ORGANIZATIONS:
      - Keep existing logic (based on sport)
    
    Args:
        predefined_queryset: Django QuerySet of PreDefinedScholarship objects
        study_level: User's study level (e.g., 'undergraduate', 'master', 'phd')
        subject: User's subject/program (e.g., 'economics', 'engineering', 'law')
        role: User's role ('Individual', 'Organisation', 'Privatperson', 'Organisation')
        sport: User's sport (for organizations)
        debug: Whether to print debug info
    
    Returns:
        Tuple of (predefined_always, predefined_filtered) QuerySets
    """
    from django.db.models import Q
    
    # Normalize role input
    is_individual = role and role.lower() in ['individual', 'privatperson']
    is_org = role and role.lower() in ['organisation', 'organization']
    
    if debug:
        print(f"\n[PREDEFINED STUDY LEVEL FILTER]")
        print(f"  Role: {role} (is_individual={is_individual})")
        print(f"  Study Level: {study_level}")
        print(f"  Subject: {subject}")
        print(f"  Sport: {sport}")
    
    if is_individual:
        # For individuals: filter by study level
        # Determine which study level to filter by
        study_level_filter = None
        if study_level:
            study_level_lower = study_level.lower()
            
            if any(t in study_level_lower for t in [
                'undergraduate', 'bachelor', 'kandidat', 'kandidatnivå', 'grundnivå'
            ]):
                    study_level_filter = 'undergraduate'
            elif any(t in study_level_lower for t in [
                    'master', 'postgraduate', 'masternivå', 'magister'
            ]):
                    study_level_filter = 'master'
            elif any(t in study_level_lower for t in [
                    'phd', 'doctoral', 'doktorand', 'forskarutbildning',
                    'doktorsexamen', 'licentiat'
            ]):
                    study_level_filter = 'phd'
        
        # Filter "always" scholarships by study level
        # Include if: study_level='all' OR study_level matches user's level OR study_level is null/empty
        predefined_always = predefined_queryset.filter(
            subject='always'
        ).filter(
            Q(study_level__isnull=True) | 
            Q(study_level='') | 
            Q(study_level='all') |
            Q(study_level=study_level_filter)
        )
        
        # Start with non-always scholarships
        predefined_filtered = predefined_queryset.exclude(subject='always')
        
        # Map study_level_filter to applicable subjects
        applicable_subjects = []
        if study_level_filter == 'undergraduate':
            # Undergraduate subjects
            applicable_subjects = [
                'engineering_technology',
                'economics_business',
                'medicine_health',
                'cs_it_data',
                'education_pedagogy',
                'psychology_behavioral',
                'law_political',
                'environment_sustainability',
                'design_architecture_arts',
                'biology_chemistry_life',
            ]
        elif study_level_filter == 'master':
            # Master's subjects
            applicable_subjects = [
                'public_health_epidemiology',
                'eng_tech_advanced',
                'business_management',
                'cs_digital_data_advanced',
                'education_didactics',
                'environment_urban',
                'life_science_biotech',
                'law_llm',
                'design_creative_advanced',
                'social_sciences',
            ]
        elif study_level_filter == 'phd':
            # PhD subjects
            applicable_subjects = [
                'phd_engineering_technology',
                'phd_economics',
                'phd_medicine',
                'phd_law',
                'phd_arts_culture',
            ]
        
        # Filter by applicable subjects
        if applicable_subjects:
            predefined_filtered = predefined_filtered.filter(
                subject__in=applicable_subjects
            ).filter(
                Q(study_level__isnull=True) | 
                Q(study_level='') | 
                Q(study_level='all') |
                Q(study_level=study_level_filter)
            )
        else:
            # For unknown level, return only "always"
            predefined_filtered = predefined_filtered.none()
        
        # Additionally filter by subject if provided
        if subject and subject != 'always':
            predefined_filtered = predefined_filtered.filter(subject=subject)
        
        if debug:
            print(f"  -> Study Level Filter: {study_level_filter}")
            print(f"  -> Individual: filtered to {predefined_filtered.count()} subject-specific + {predefined_always.count()} always")
    
    elif is_org:
        # For organizations: keep sport filtering (unchanged from original logic)
        predefined_always = predefined_queryset.filter(subject='always')
        predefined_filtered = predefined_queryset.exclude(subject='always')
        
        if debug:
            print(f"  -> Organization: using sport-based filtering (original logic)")
    else:
        # Unknown role: return empty
        predefined_always = predefined_queryset.none()
        predefined_filtered = predefined_queryset.none()
        
        if debug:
            print(f"  -> Unknown role: returning empty")
    
    return predefined_always, predefined_filtered

# if __name__ == "__main__":
#     results = find_scholarships_v2(
#         user_purpose="I am interested to law related subjects for my undergraduate program",
#         #subject="Economics, Business Administration & Management",
#         user_type="Individual",
#         #elite_athlete=False,
#         #sport="Ice Hockey",
#         municipality="Stockholm",
#         municipality_filter=False,
#         #study_level="university,Undergraduate",
#         gender="male",
#         #language="en",
#         top_k=200,
#         debug=True,
#         use_llm_rerank=True
#     )

#     formatted = format_scholarship_json(results, output_language="en")
#     print(formatted)
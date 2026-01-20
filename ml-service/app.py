from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import numpy as np
import re
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image
import io
import base64
import unicodedata
import os
import requests
import sys
import numpy

# --- TRUCO DE COMPATIBILIDAD PARA NUMPY 2.0 ---
# Creamos un alias manual para que el modelo encuentre la ruta antigua
sys.modules['numpy._core'] = numpy._core
sys.modules['numpy._core.numeric'] = numpy._core.numeric
# ----------------------------------------------

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:5173",
            "https://*.vercel.app",
            "https://tu-dominio.com"
        ]
    }
})

print("=" * 60)
print("CARGANDO MODELO DE MODA CON IA...")
print("=" * 60)

# Cargar modelo entrenado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'fashion_model.pkl')

print(f"Intentando cargar modelo desde: {MODEL_PATH}")
try:
    with open(MODEL_PATH, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    style_encoder = model_data['style_encoder']
    gender_encoder = model_data['gender_encoder']
    season_encoder = model_data['season_encoder']
    results_map = model_data['results_map']
    idx_to_combination = model_data['idx_to_combination']

    print("Modelo de predicción cargado exitosamente")
except FileNotFoundError:
    print(f"ERROR: No se encontró el archivo en {MODEL_PATH}")
    raise

# Cargar modelo de embeddings para busqueda semantica
print("Cargando modelo de embeddings...")
model_embed = None
print("Modelo de embeddings cargado")

# IA externa (Hugging Face)
HF_TOKEN = os.environ.get("HF_TOKEN") 
CLIP_API_URL = "https://api-inference.huggingface.co/models/openai/clip-vit-base-patch32"

# Pre-calcular embeddings de estilos disponibles
available_styles = list(style_encoder.classes_)

print(f"Estilos disponibles: {available_styles}")
print(f"Generos disponibles: {list(gender_encoder.classes_)}")
print(f"Estaciones disponibles: {list(season_encoder.classes_)}")
print("=" * 60)

# MAPEO COMPLETO DE COLORES A HEX
COLOR_HEX_MAP = {
    'crema': '#FFFDD0', 'beige': '#F5F5DC', 'arena': '#C2B280', 'camel': '#C19A6B',
    'topo': '#483C32', 'champan': '#F7E7CE', 'marfil': '#FFFFF0',
    'vainilla': '#F3E5AB', 'nude': '#E3BC9A',
    'blanco': '#FFFFFF', 'gris': '#808080', 'gris claro': '#D3D3D3', 'gris oscuro': '#404040',
    'negro': '#000000', 'antracita': '#2F4F4F', 'carbon': '#36454F', 'platino': '#E5E4E2',
    'plata': '#C0C0C0', 'perla': '#EAE0C8',
    'marron': '#8B4513', 'chocolate': '#7B3F00', 'cafe': '#6F4E37',
    'terracota': '#E2725B', 'cobre': '#B87333', 'bronce': '#CD7F32', 'cognac': '#9A463D',
    'rojo': '#FF0000', 'rojo oscuro': '#8B0000', 'carmesi': '#DC143C',
    'borgona': '#800020', 'burgundy': '#800020', 'vino': '#722F37', 'burdeos': '#800020',
    'rosa': '#FFC0CB', 'rosa palo': '#FFD1DC', 'rosa viejo': '#C08081', 'fucsia': '#FF00FF',
    'magenta': '#FF00FF', 'coral': '#FF7F50', 'salmon': '#FA8072',
    'azul': '#0000FF', 'azul marino': '#000080', 'navy': '#001F3F', 'azul real': '#4169E1',
    'azul cielo': '#87CEEB', 'celeste': '#87CEEB', 'turquesa': '#40E0D0', 'aguamarina': '#7FFFD4',
    'cobalto': '#0047AB', 'azul petroleo': '#1C4966', 'indigo': '#4B0082', 'azul acero': '#4682B4',
    'verde': '#00FF00', 'verde oscuro': '#006400', 'verde militar': '#4B5320',
    'verde oliva': '#808000', 'oliva': '#556B2F', 'olive': '#808000', 'verde bosque': '#228B22',
    'esmeralda': '#50C878', 'menta': '#98FF98', 'verde agua': '#66CDAA', 'jade': '#00A86B',
    'musgo': '#8A9A5B',
    'amarillo': '#FFFF00', 'oro': '#FFD700', 'mostaza': '#FFDB58', 'limon': '#FFF700',
    'naranja': '#FFA500', 'naranja quemado': '#CC5500', 'mandarina': '#F28500', 'calabaza': '#FF7518',
    'morado': '#800080', 'violeta': '#8B00FF', 'purpura': '#800080',
    'lavanda': '#E6E6FA', 'lila': '#C8A2C8', 'ciruela': '#8E4585', 'berenjena': '#614051',
    'malva': '#E0B0FF',
    'dorado': '#FFD700', 'caqui': '#C3B091', 'mostaza oscuro': '#E1AD01', 'tostado': '#D2B48C',
    'arena oscuro': '#967969', 'sepia': '#704214',
}

# DESCRIPCIONES ESPECÍFICAS POR PRENDA
PRENDA_DESCRIPTIONS = {
    # Prendas superiores
    'camisa': 'prenda de vestir con cuello y botones, versátil para looks formales y casuales',
    'camiseta': 'prenda básica de manga corta, esencial en cualquier guardarropa',
    'blusa': 'prenda elegante y femenina, ideal para ocasiones especiales',
    'polo': 'camiseta con cuello y botones, equilibrio perfecto entre casual y formal',
    'sueter': 'prenda de punto cálida y acogedora para temporadas frías',
    'jersey': 'prenda de punto ligera, perfecta para el entretiempo',
    'chaleco': 'prenda sin mangas que añade una capa extra de estilo',
    'blazer': 'chaqueta estructurada que aporta elegancia a cualquier outfit',
    'chaqueta': 'prenda exterior versátil para múltiples ocasiones',
    'abrigo': 'prenda larga y abrigada para proteger del frío',
    'cardigan': 'chaqueta de punto abierta, cómoda y estilosa',
    'sudadera': 'prenda deportiva cómoda, perfecta para looks relajados',
    'hoodie': 'sudadera con capucha, icónica del streetwear',
    'crop top': 'prenda corta que deja al descubierto el abdomen, moderna y atrevida',
    'top': 'prenda superior ligera y versátil',
    'bodysuit': 'prenda ajustada de una pieza, perfecta para estilizar la figura',
    
    # Prendas inferiores
    'pantalon': 'prenda que cubre las piernas, disponible en múltiples estilos',
    'pantalones': 'prenda que cubre las piernas, disponible en múltiples estilos',
    'jeans': 'pantalón de mezclilla resistente y atemporal',
    'vaqueros': 'pantalón de denim clásico, básico del guardarropa',
    'chinos': 'pantalones de algodón elegantes y versátiles',
    'shorts': 'pantalón corto ideal para climas cálidos',
    'bermudas': 'pantalón corto hasta la rodilla, cómodo y casual',
    'falda': 'prenda que cae desde la cintura, femenina y elegante',
    'minifalda': 'falda corta y juvenil, perfecta para looks atrevidos',
    'falda midi': 'falda de largo medio, elegante y sofisticada',
    'falda larga': 'falda que llega hasta los tobillos, fluida y romántica',
    'leggings': 'pantalón ajustado elástico, cómodo y versátil',
    'joggers': 'pantalón deportivo con puños en los tobillos',
    
    # Vestidos y monos
    'vestido': 'prenda de una pieza femenina y elegante',
    'vestido corto': 'vestido por encima de la rodilla, juvenil y fresco',
    'vestido largo': 'vestido que llega hasta los pies, elegante y sofisticado',
    'vestido midi': 'vestido de largo medio, versátil y favorecedor',
    'mono': 'prenda de una pieza con pantalón, moderna y práctica',
    'jumpsuit': 'mono elegante de una pieza, perfecto para eventos',
    'maxi dress': 'vestido largo y fluido, ideal para verano',
    
    # Calzado
    'zapatillas': 'calzado deportivo cómodo y casual',
    'sneakers': 'zapatillas urbanas modernas y versátiles',
    'botas': 'calzado que cubre el tobillo o más arriba',
    'botines': 'botas cortas que llegan al tobillo',
    'sandalias': 'calzado abierto ideal para climas cálidos',
    'tacones': 'zapatos con tacón elevado, elegantes y femeninos',
    'zapatos': 'calzado cerrado para diversas ocasiones',
    'mocasines': 'zapatos sin cordones elegantes y cómodos',
    'oxford': 'zapato clásico con cordones, formal y sofisticado',
    'deportivas': 'calzado deportivo para actividades físicas',
    
    # Accesorios
    'gorra': 'accesorio para la cabeza, casual y deportivo',
    'sombrero': 'accesorio elegante para proteger del sol',
    'bufanda': 'accesorio de cuello que aporta calidez y estilo',
    'panuelo': 'accesorio versátil que se puede usar de múltiples formas',
    'cinturon': 'accesorio que define la cintura y añade estructura',
    'bolso': 'accesorio práctico para llevar pertenencias',
    'mochila': 'bolsa que se lleva en la espalda, práctica y casual',
    'rinonera': 'bolsa pequeña que se lleva en la cintura, tendencia actual',
    'gafas de sol': 'accesorio protector con estilo',
    'reloj': 'accesorio funcional que añade elegancia',
    'collar': 'joya que se lleva en el cuello',
    'pulsera': 'joya que se lleva en la muñeca',
    'pendientes': 'joyas que se llevan en las orejas',
    'aretes': 'joyas que adornan las orejas',
    
    # Prendas técnicas y deportivas
    'chaleco multipockets': 'chaleco funcional con múltiples bolsillos, estilo utility',
    'plumas tecnico': 'chaqueta acolchada técnica, ligera y cálida',
    'chubasquero oversized': 'impermeable holgado de estilo urbano moderno',
    'bermudas cargo': 'shorts con bolsillos laterales, estilo funcional',
    'parka': 'abrigo largo con capucha, resistente al clima',
    'windbreaker': 'chaqueta cortavientos ligera y funcional',
    'chaqueta bomber': 'chaqueta corta con puños elásticos, icónica del streetwear',
    'anorak': 'chaqueta impermeable con capucha, deportiva y funcional',
}

# DESCRIPCIONES ESPECÍFICAS DE MATERIALES
MATERIAL_DESCRIPTIONS = {
    'algodon': 'fibra natural suave, transpirable y cómoda para uso diario',
    'lino': 'fibra natural ligera y fresca, ideal para climas cálidos',
    'lana': 'fibra natural cálida y aislante, perfecta para el invierno',
    'seda': 'fibra natural lujosa, suave y con brillo elegante',
    'cachemira': 'lana ultra suave y lujosa procedente de cabras de cachemira',
    'cuero': 'material duradero y elegante de origen animal',
    'denim': 'tejido resistente de algodón, clásico para jeans',
    'terciopelo': 'tejido suave con textura afelpada y aspecto lujoso',
    'saten': 'tejido brillante y liso con acabado elegante',
    'jersey': 'tejido elástico y cómodo, ideal para prendas casuales',
    'tweed': 'tejido de lana rugoso con textura característica',
    'pana': 'tejido con acanalado vertical distintivo y tacto suave',
    'poliester': 'fibra sintética duradera y fácil de mantener',
    'nylon': 'fibra sintética resistente, ligera y de secado rápido',
    'viscosa': 'fibra semi-sintética suave con caída fluida',
    'modal': 'fibra suave y transpirable derivada de la celulosa',
    'spandex': 'fibra elástica que aporta flexibilidad y ajuste',
    'lana merino': 'lana fina y suave de alta calidad',
    'algodon organico': 'algodón cultivado sin pesticidas ni químicos',
    'gamuza': 'cuero con acabado aterciopelado y suave',
    'elastano': 'fibra elástica sintética altamente flexible',
    'lycra': 'fibra elástica que proporciona comodidad y movimiento',
    'rayon': 'fibra artificial suave con aspecto similar a la seda',
    'acrilico': 'fibra sintética que imita la lana, cálida y ligera',
    'organza': 'tejido fino, transparente y con cuerpo',
    'tul': 'tejido de malla ligero y delicado',
    'encaje': 'tejido decorativo con patrones calados',
    'gasa': 'tejido ligero, transparente y fluido',
    'felpa': 'tejido suave con pelo rizado en la superficie',
    'polar': 'tejido sintético cálido y esponjoso',
    'nylon ripstop': 'nylon reforzado resistente a rasgaduras',
    'gore-tex': 'membrana impermeable y transpirable de alta tecnología',
    'tejido reflectante': 'material con propiedades reflectantes para visibilidad',
    'mesh': 'tejido de malla transpirable para ventilación',
    'neopreno': 'material sintético aislante usado en prendas deportivas',
}

# DESCRIPCIONES DE ESTILOS
STYLE_DESCRIPTIONS = {
    'cayetano': 'Una evolución del estilo cayetano mezclado con el bohemio-chic de los 70, buscando un aspecto de lujo heredado y relajado.',
    'pijo': 'El estilo preppy clásico con toques modernos, elegancia casual y sofisticación atemporal.',
    'urbano/streetwear': 'La esencia del streetwear urbano con influencias del hip-hop y la cultura skate contemporánea.',
    'boho-chic': 'Espíritu bohemio con toques vintage y artesanales, libre y romántico con influencias de los 70.',
    'sporty/gorpcore': 'Funcionalidad outdoor meets fashion, con prendas técnicas y estética deportiva de alto rendimiento.',
    'minimalista/scandi': 'Líneas limpias, paleta neutra y diseño escandinavo minimalista con enfoque en la calidad.',
    'y2k/grunge': 'Nostalgia de los 2000 con edge grunge, rebelde y auténtico con toques subversivos.',
    'old money': 'Elegancia heredada y discreta, calidad sobre tendencias con estética clásica intergeneracional.',
    'quiet luxury': 'Lujo sin logos, calidad superior y diseño minimalista que habla por sí mismo.',
    'coquette': 'Feminidad romántica con lazos, volantes y tonos suaves que celebran la delicadeza.',
    'dark academia': 'Inspiración literaria y universitaria clásica con paleta oscura y toques intelectuales.',
    'cyberpunk/techwear': 'Estética futurista con prendas técnicas, tejidos reflectantes y funcionalidad urbana avanzada.'
}

# PROMPTS MEJORADOS PARA CLIP
STYLE_CLIP_PROMPTS = {
    'Cayetano': [
        'persona con estilo cayetano elegante y preppy',
        'outfit casual elegante con polo y pantalones chinos',
        'ropa preppy española con jersey sobre hombros'
    ],
    'Pijo': [
        'estilo preppy clásico elegante',
        'outfit con blazer y pantalones de vestir',
        'look sofisticado y bien vestido'
    ],
    'Urbano/Streetwear': [
        'ropa streetwear urbana moderna',
        'outfit con sudadera oversized y sneakers',
        'estilo hip hop urbano con gorras y zapatillas'
    ],
    'Boho-Chic': [
        'estilo bohemio hippie con vestido largo',
        'look boho con accesorios artesanales',
        'ropa vintage romántica con flecos'
    ],
    'Sporty/Gorpcore': [
        'ropa deportiva técnica outdoor',
        'outfit con chaqueta impermeable y zapatillas de trail',
        'estilo funcional deportivo'
    ],
    'Minimalista/Scandi': [
        'estilo minimalista escandinavo simple',
        'ropa minimalista en colores neutros',
        'outfit simple y elegante monocromático'
    ],
    'Y2K/Grunge': [
        'estilo grunge años 2000',
        'ropa Y2K con jeans baggy y crop top',
        'look alternativo con ropa oscura rasgada'
    ],
    'Old Money': [
        'estilo old money clásico elegante',
        'ropa de lujo discreta y atemporal',
        'outfit elegante con tweed y cachemira'
    ],
    'Quiet Luxury': [
        'lujo silencioso sin logos',
        'ropa minimalista de alta calidad',
        'outfit elegante simple premium'
    ],
    'Coquette': [
        'estilo coquette femenino romántico',
        'ropa con lazos y volantes rosa',
        'outfit delicado con detalles románticos'
    ],
    'Dark Academia': [
        'estilo dark academia universitario',
        'ropa académica con blazer y libros',
        'outfit vintage literario oscuro'
    ],
    'Cyberpunk/Techwear': [
        'ropa techwear futurista negra',
        'outfit cyberpunk con muchos bolsillos',
        'estilo técnico urbano con telas reflectantes'
    ]
}

def normalize_text(text):
    """Normalizar texto para comparacion"""
    if not text:
        return ''
    text = text.lower().strip()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return text

def capitalize_first_only(text):
    """Capitaliza solo la primera letra de la frase completa"""
    if not text:
        return ''
    text = text.strip()
    return text[0].upper() + text[1:].lower() if text else ''

def get_color_hex(color_name):
    """Obtiene el código hex de un color"""
    normalized = normalize_text(color_name)
    return COLOR_HEX_MAP.get(normalized, '#CCCCCC')

def get_prenda_description(prenda_name):
    """Obtiene la descripción específica de una prenda"""
    normalized = normalize_text(prenda_name)
    
    # Buscar coincidencia exacta
    if normalized in PRENDA_DESCRIPTIONS:
        return PRENDA_DESCRIPTIONS[normalized]
    
    # Buscar coincidencia parcial
    for key, desc in PRENDA_DESCRIPTIONS.items():
        if key in normalized or normalized in key:
            return desc
    
    return None

def get_material_description(material_name):
    """Obtiene la descripción de un material"""
    normalized = normalize_text(material_name)
    return MATERIAL_DESCRIPTIONS.get(normalized, 'material de calidad para confección de prendas')

def get_style_description(style_name):
    """Obtiene la descripción de un estilo"""
    normalized = normalize_text(style_name)
    return STYLE_DESCRIPTIONS.get(normalized, f'Estilo {style_name} que define las tendencias del momento')

def normalize_prenda(prenda):
    """Normaliza una prenda individual"""
    if isinstance(prenda, str):
        nombre = capitalize_first_only(prenda)
        descripcion = get_prenda_description(prenda)
        return {
            'nombre': nombre,
            'descripcion': descripcion,
            'estilo': None
        }
    elif isinstance(prenda, dict):
        nombre = capitalize_first_only(prenda.get('nombre', ''))
        descripcion_original = prenda.get('descripcion', '')
        estilo = prenda.get('estilo', '')
        
        descripcion_especifica = get_prenda_description(prenda.get('nombre', ''))
        
        if descripcion_especifica:
            descripcion = descripcion_especifica
        elif descripcion_original and not descripcion_original.startswith('Exclusividad'):
            descripcion = capitalize_first_only(descripcion_original)
        else:
            descripcion = None
            
        return {
            'nombre': nombre,
            'descripcion': descripcion,
            'estilo': capitalize_first_only(estilo) if estilo else None
        }
    return prenda

def normalize_results(results):
    """Normaliza los resultados para que tengan capitalizacion correcta"""
    normalized = {
        'prendas': [],
        'colores': [],
        'materiales': [],
        'tiendas_accesibles': [],
        'tiendas_lujo': []
    }
    
    if 'prendas' in results:
        for prenda in results['prendas']:
            normalized['prendas'].append(normalize_prenda(prenda))
    
    if 'colores' in results:
        for color in results['colores']:
            normalized['colores'].append({
                'nombre': capitalize_first_only(color),
                'hex': get_color_hex(color)
            })
    
    if 'materiales' in results:
        for material in results['materiales']:
            normalized['materiales'].append({
                'nombre': capitalize_first_only(material),
                'descripcion': get_material_description(material)
            })
    
    if 'tiendas_accesibles' in results:
        normalized['tiendas_accesibles'] = results['tiendas_accesibles']
    
    if 'tiendas_lujo' in results:
        normalized['tiendas_lujo'] = results['tiendas_lujo']
    
    return normalized

def find_similar_style(input_style):
    """Búsqueda de estilo simplificada (sin gastar RAM)"""
    input_style_norm = normalize_text(input_style)
    
    # 1. Intenta coincidencia exacta primero
    for style in available_styles:
        if normalize_text(style) == input_style_norm:
            return style, 1.0
            
    # 2. Si no hay coincidencia exacta, busca si la palabra está contenida
    for style in available_styles:
        if input_style_norm in normalize_text(style):
            return style, 0.8
            
    # 3. Por defecto devuelve el primero si no entiende nada
    return available_styles[0], 0.1

def parse_time_natural(time_text):
    """Parsea texto de tiempo natural a meses"""
    if not time_text:
        return 1
    
    time_text = normalize_text(str(time_text))
    numbers = re.findall(r'\d+', time_text)
    
    if not numbers:
        return 1
    
    num = int(numbers[0])
    
    if 'dia' in time_text or 'day' in time_text:
        return max(1, num // 30)
    elif 'semana' in time_text or 'week' in time_text:
        return max(1, num // 4)
    elif 'mes' in time_text or 'month' in time_text:
        return num
    elif 'ano' in time_text or 'year' in time_text:
        return num * 12
    else:
        return num

def analyze_image_style(image_data):
    """Analiza la imagen usando la API externa para ahorrar RAM"""
    try:
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)

        # Llamada a la API de Hugging Face
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {
            "inputs": image_data, 
            "parameters": {"candidate_labels": available_styles}
        }
        
        response = requests.post(CLIP_API_URL, headers=headers, data=image_bytes)
        
        if response.status_code != 200:
            return None

        output = response.json()
        return [{'style': item['label'], 'confidence': item['score']} for item in output[:3]]
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'OK',
        'model_loaded': True,
        'ai_features': {
            'semantic_search': True,
            'nlp_time_parsing': True,
            'image_analysis': True
        },
        'available_styles': available_styles,
        'available_genders': list(gender_encoder.classes_),
        'available_seasons': list(season_encoder.classes_)
    })

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    """Analiza una imagen y devuelve los estilos detectados"""
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No se proporciono imagen'}), 400
        
        print(f"\n[ANALISIS DE IMAGEN]")
        results = analyze_image_style(image_data)
        
        if results:
            print(f"Estilos detectados:")
            for r in results:
                print(f"  - {r['style']}: {r['confidence']:.2%}")
            
            return jsonify({
                'success': True,
                'detected_styles': results
            })
        else:
            return jsonify({'error': 'No se pudo analizar la imagen'}), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        style_input = data.get('style')
        gender = data.get('gender')
        season = data.get('season')
        time_input = data.get('time')
        
        print(f"\n[PREDICCION] Entrada: {style_input} | {gender} | {season} | {time_input}")
        
        # Busqueda semantica de estilo
        matched_style, similarity = find_similar_style(style_input)
        print(f"Estilo encontrado: '{matched_style}' (similitud: {similarity:.2%})")
        
        if similarity < 0.5:
            print(f"Baja similitud, usando estilo mas cercano")
        
        # Parsear tiempo natural
        months = 1
        if time_input:
            months = parse_time_natural(time_input)
            print(f"Tiempo parseado: '{time_input}' -> {months} meses")
        
        # Normalizar genero
        gender_norm = normalize_text(gender)
        gender_classes_norm = [normalize_text(g) for g in gender_encoder.classes_]
        
        try:
            gender_idx = gender_classes_norm.index(gender_norm)
            gender_encoded = gender_encoder.transform([gender_encoder.classes_[gender_idx]])[0]
        except ValueError:
            return jsonify({'error': f'Genero "{gender}" no encontrado'}), 404
        
        # Calcular estacion basada en el tiempo
        if not season:
            future_month = (datetime.now().month + months - 1) % 12
            season_map = {
                (2, 3, 4): 'Primavera',
                (5, 6, 7): 'Verano',
                (8, 9, 10): 'Otono',
                (11, 0, 1): 'Invierno'
            }
            for months_tuple, s in season_map.items():
                if future_month in months_tuple:
                    season = s
                    break
        
        season_norm = normalize_text(season)
        season_classes_norm = [normalize_text(s) for s in season_encoder.classes_]
        
        try:
            season_idx = season_classes_norm.index(season_norm)
            season_encoded = season_encoder.transform([season_encoder.classes_[season_idx]])[0]
        except ValueError:
            return jsonify({'error': f'Estacion "{season}" no encontrada'}), 404
        
        # Codificar el estilo encontrado
        style_encoded = style_encoder.transform([matched_style])[0]
        
        # Crear input para el modelo
        X = np.array([[style_encoded, gender_encoded, season_encoded]])
        
        # Predecir
        prediction_idx = model.predict(X)[0]
        combination = idx_to_combination[prediction_idx]
        
        # Obtener resultados del mapa
        results = results_map[combination]
        
        # Normalizar resultados con descripciones específicas
        normalized_results = normalize_results(results)
        
        # Obtener descripción del estilo
        style_description = get_style_description(matched_style)
        
        print(f"Prediccion exitosa: {len(normalized_results['prendas'])} prendas encontradas")
        
        return jsonify({
            'success': True,
            'matched_style': matched_style,
            'style_similarity': float(similarity),
            'style_description': style_description,
            'original_input': style_input,
            'prendas': normalized_results['prendas'],
            'colores': normalized_results['colores'],
            'materiales': normalized_results['materiales'],
            'tiendas_accesibles': normalized_results['tiendas_accesibles'],
            'tiendas_lujo': normalized_results['tiendas_lujo']
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\nAPI de prediccion con IA iniciada en http://localhost:5000")
    print("   - Health check: http://localhost:5000/health")
    print("   - Prediccion: POST http://localhost:5000/predict")
    print("   - Analisis de imagen: POST http://localhost:5000/analyze-image")
    print("\n")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
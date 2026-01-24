import  { analyzeImage, predictFashion } from './services/api.js';
import './index.css';
import React, { useState, useRef, useEffect } from 'react';

const styleOptions = [
  'Cayetano', 'Pijo', 'Urbano/Streetwear', 'Boho-Chic', 
  'Sporty/Gorpcore', 'Minimalista/Scandi', 'Y2K/Grunge', 
  'Old Money', 'Quiet Luxury', 'Coquette', 'Dark Academia', 
  'Cyberpunk/Techwear'
];

const genderOptions = ['Masculino', 'Femenino'];

export default function App() {
  const [style, setStyle] = useState('');
  const [gender, setGender] = useState('');
  const [time, setTime] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [detectedStyles, setDetectedStyles] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [savedPredictions, setSavedPredictions] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [predictedDate, setPredictedDate] = useState('');
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);

  const isReady = style && gender && time;

  useEffect(() => {
    const saved = localStorage.getItem('fashionPredictions');
    if (saved) {
      try {
        setSavedPredictions(JSON.parse(saved));
      } catch (e) {
        console.error('Error cargando predicciones guardadas:', e);
      }
    }
    
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const calculatePredictedDate = (timeText) => {
    if (!timeText) return '';
    
    const normalizedTime = timeText.toLowerCase();
    const numbers = timeText.match(/\d+/);
    const num = numbers ? parseInt(numbers[0]) : 1;
    
    const now = new Date();
    let futureDate = new Date(now);
    
    if (normalizedTime.includes('dia') || normalizedTime.includes('day')) {
      futureDate.setDate(futureDate.getDate() + num);
    } else if (normalizedTime.includes('semana') || normalizedTime.includes('week')) {
      futureDate.setDate(futureDate.getDate() + (num * 7));
    } else if (normalizedTime.includes('mes') || normalizedTime.includes('month')) {
      futureDate.setMonth(futureDate.getMonth() + num);
    } else if (normalizedTime.includes('año') || normalizedTime.includes('year')) {
      futureDate.setFullYear(futureDate.getFullYear() + num);
    } else {
      futureDate.setMonth(futureDate.getMonth() + num);
    }
    
    const months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
    
    return `${months[futureDate.getMonth()]} de ${futureDate.getFullYear()}`;
  };

  const savePrediction = () => {
    if (!result) return;
    
    const newPrediction = {
      id: Date.now(),
      date: new Date().toLocaleString('es-ES'),
      style: style,
      gender: gender,
      time: time,
      predictedDate: predictedDate,
      data: result
    };
    
    const updated = [newPrediction, ...savedPredictions];
    setSavedPredictions(updated);
    localStorage.setItem('fashionPredictions', JSON.stringify(updated));
    alert('Predicción guardada exitosamente');
  };

  const deletePrediction = (id) => {
    const updated = savedPredictions.filter(p => p.id !== id);
    setSavedPredictions(updated);
    localStorage.setItem('fashionPredictions', JSON.stringify(updated));
  };

  const loadPrediction = (prediction) => {
    setStyle(prediction.style);
    setGender(prediction.gender);
    setTime(prediction.time);
    setPredictedDate(prediction.predictedDate || '');
    setResult(prediction.data);
    setShowHistory(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const startCamera = async () => {
    try {
      setError(null);
      setCameraReady(false);
      setShowCamera(true);
      
      const constraints = {
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play()
            .then(() => {
              setCameraReady(true);
            })
            .catch(err => {
              setError('Error al iniciar reproducción del video');
            });
        };
      }
    } catch (err) {
      setShowCamera(false);
      setError(`No se pudo acceder a la cámara: ${err.message}`);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setShowCamera(false);
    setCameraReady(false);
  };

  const captureImage = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    setCapturedImage(imageData);
    stopCamera();
    await analyzeImage(imageData);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (event) => {
      const imageData = event.target.result;
      setCapturedImage(imageData);
      await analyzeImage(imageData);
    };
    reader.readAsDataURL(file);
  };

  const analyzeImage = async (imageData) => {
    setAnalyzing(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:5000/analyze-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData })
      });
      
      if (!response.ok) {
        throw new Error('Error al analizar la imagen');
      }
      
      const data = await response.json();
      setDetectedStyles(data.detected_styles);
      
      if (data.detected_styles && data.detected_styles.length > 0) {
        setStyle(data.detected_styles[0].style);
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setAnalyzing(false);
    }

    const result = await analyzeImage(imageData);
  };

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const predicted = calculatePredictedDate(time);
      setPredictedDate(predicted);
      
      const response = await fetch('http://localhost:5000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          style: style,
          gender: gender,
          time: time,
          season: ''
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'No se encontraron coincidencias');
      }
      
      const data = await response.json();
      console.log('Datos recibidos del servidor:', data);
      setResult(data);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }

    const data = await predictFashion({
      style: style,
      gender: gender,
      time: time,
      season: ''
    });
  };

  const resetSelection = () => {
    setStyle('');
    setGender('');
    setTime('');
    setResult(null);
    setError(null);
    setDetectedStyles(null);
    setCapturedImage(null);
    setPredictedDate('');
  };

  return (
    <div className="main-container">
      <div className="header-section">
        <h1 className="main-title">Bienvenida/o a MF</h1>
        <p className="subtitle">Predicción inteligente de tendencias con IA</p>
        <button 
          onClick={() => setShowHistory(!showHistory)}
          className="btn-history"
        >
          {showHistory ? 'Ocultar historial' : 'Ver historial'} ({savedPredictions.length})
        </button>
      </div>

      {showHistory && (
        <div className="history-section">
          <h3 className="section-title">Historial de predicciones</h3>
          {savedPredictions.length === 0 ? (
            <p className="empty-history">No hay predicciones guardadas</p>
          ) : (
            <div className="history-list">
              {savedPredictions.map(pred => (
                <div key={pred.id} className="history-item">
                  <div className="history-item-header">
                    <div>
                      <h4>{pred.style}</h4>
                      <p className="history-date">{pred.date}</p>
                      <p className="history-details">{pred.gender} - {pred.time}</p>
                      {pred.predictedDate && (
                        <p className="history-predicted">Predicción para: {pred.predictedDate}</p>
                      )}
                    </div>
                    <div className="history-actions">
                      <button 
                        onClick={() => loadPrediction(pred)}
                        className="btn-load"
                      >
                        Cargar
                      </button>
                      <button 
                        onClick={() => deletePrediction(pred.id)}
                        className="btn-delete"
                      >
                        Eliminar
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="image-analysis-section">
        <h3 className="section-title">Análisis visual</h3>
        
        {showCamera && (
          <div className="camera-container">
            {!cameraReady && (
              <div className="camera-loading">
                <div className="spinner"></div>
                <p>Iniciando cámara...</p>
              </div>
            )}
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted
              className="video-preview"
            />
            <div className="camera-buttons">
              <button 
                onClick={captureImage} 
                className="btn-capture"
                disabled={!cameraReady}
              >
                Capturar y analizar
              </button>
              <button onClick={stopCamera} className="btn-cancel-camera">
                Cancelar
              </button>
            </div>
          </div>
        )}

        {capturedImage && !analyzing && !showCamera && (
          <div className="captured-preview">
            <h4>Imagen capturada:</h4>
            <img src={capturedImage} alt="Captura" className="captured-image" />
          </div>
        )}

        {analyzing && (
          <div className="analyzing-message">
            <span className="spinner"></span>
            Analizando imagen con IA...
          </div>
        )}

        {detectedStyles && (
          <div className="detected-styles">
            <h4>Estilos detectados:</h4>
            <div className="style-results">
              {detectedStyles.map((item, idx) => (
                <div key={idx} className="style-result-item">
                  <span className="style-name">{item.style}</span>
                  <span className="confidence-bar">
                    <span 
                      className="confidence-fill" 
                      style={{ width: `${item.confidence * 100}%` }}
                    ></span>
                  </span>
                  <span className="confidence-text">
                    {(item.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="image-controls">
          <button 
            onClick={showCamera ? stopCamera : startCamera}
            className="btn-camera"
          >
            {showCamera ? 'Cerrar cámara' : 'Abrir cámara'}
          </button>
          <button 
            onClick={() => fileInputRef.current?.click()}
            className="btn-upload"
          >
            Subir imagen
          </button>
          <input 
            ref={fileInputRef}
            type="file" 
            accept="image/*" 
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </div>
      </div>

      <div className="form-container">
        <div className="input-group">
          <label htmlFor="style-input" className="input-label">
            Estilo (escribe o selecciona)
          </label>
          <input 
            type="text"
            id="style-input"
            className="text-input"
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            placeholder="Ej: minimalista, vintage, streetwear..."
            list="style-suggestions"
          />
          <datalist id="style-suggestions">
            {styleOptions.map(opt => (
              <option key={opt} value={opt} />
            ))}
          </datalist>
          <p className="input-hint">
            Escribe cualquier estilo, la IA encontrará el más similar
          </p>
        </div>

        <div className="input-group">
          <label htmlFor="gender-input" className="input-label">Género</label>
          <select 
            id="gender-input"
            className="select-input"
            value={gender}
            onChange={(e) => setGender(e.target.value)}
          >
            <option value="">Selecciona un género...</option>
            {genderOptions.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label htmlFor="time-input" className="input-label">
            Tiempo (escribe en lenguaje natural)
          </label>
          <input 
            type="text"
            id="time-input"
            className="text-input"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            placeholder="Ej: en 3 meses, próximo año, 6 semanas..."
          />
          <p className="input-hint">
            Escribe como: "en 2 meses", "próximo año", "dentro de 1 semana"
          </p>
        </div>
      </div>

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {(style || gender || time) && (
        <div className="selections-display">
          <p className="selections-title">Tus selecciones:</p>
          <div className="selections-tags">
            {style && <span className="selection-tag">{style}</span>}
            {gender && <span className="selection-tag">{gender}</span>}
            {time && <span className="selection-tag">{time}</span>}
          </div>
        </div>
      )}

      <button 
        disabled={!isReady || loading} 
        onClick={handlePredict}
        className={`btn-predict ${isReady && !loading ? 'active' : 'disabled'}`}
      >
        {loading ? (
          <span className="loading-text">
            <span className="spinner"></span>
            Prediciendo con IA...
          </span>
        ) : 'Predecir'}
      </button>

      {result && (
        <div className="results-section">
          {result.style_similarity < 0.8 && (
            <div className="similarity-notice">
              Tu estilo "{result.original_input}" se asoció con "{result.matched_style}" 
              (similitud: {(result.style_similarity * 100).toFixed(0)}%)
            </div>
          )}

          <div className="result-style-banner">
            <h2 className="result-style-title">Estilo: {result.matched_style}</h2>
            {result.style_description && (
              <p className="style-description">{result.style_description}</p>
            )}
            {predictedDate && (
              <p className="prediction-intro">
                Basándome en los datos seleccionados, las predicciones para <strong>{predictedDate}</strong> son:
              </p>
            )}
          </div>

          <div className="results-grid">
            <div className="result-box">
              <h3 className="result-box-title">Prendas clave:</h3>
              <div className="prendas-list">
                {result.prendas && result.prendas.length > 0 ? (
                  result.prendas.map((prenda, idx) => (
                    <div key={idx} className="prenda-item">
                      <strong>{typeof prenda === 'string' ? prenda : prenda.nombre}</strong>
                      {typeof prenda === 'object' && (prenda.descripcion || prenda.estilo) && (
                        <p className="prenda-desc">
                          {prenda.descripcion && <span>{prenda.descripcion}</span>}
                          {prenda.estilo && (
                            <span className="prenda-estilo">
                              {prenda.descripcion ? ` (${prenda.estilo})` : prenda.estilo}
                            </span>
                          )}
                        </p>
                      )}
                    </div>
                  ))
                ) : (
                  <p>No hay prendas disponibles</p>
                )}
              </div>
            </div>

            <div className="result-box">
              <h3 className="result-box-title">Colores y materiales:</h3>
              <div className="result-box-text">
                <p><strong>Colores:</strong></p>
                {result.colores && result.colores.length > 0 ? (
                  <div className="colors-list">
                    {result.colores.map((color, idx) => (
                      <div key={idx} className="color-item-wrapper">
                        <span className="color-item">{color.nombre}</span>
                        <div 
                          className="color-preview" 
                          style={{backgroundColor: color.hex}}
                        ></div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>No hay colores disponibles</p>
                )}
                
                <p style={{marginTop: '20px'}}><strong>Materiales:</strong></p>
                {result.materiales && result.materiales.length > 0 ? (
                  <div className="materials-list">
                    {result.materiales.map((material, idx) => (
                      <div key={idx} className="material-item-wrapper">
                        <span className="material-item">{material.nombre}</span>
                        <div className="material-tooltip">{material.descripcion}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>No hay materiales disponibles</p>
                )}
              </div>
            </div>

            <div className="result-box">
              <h3 className="result-box-title">Tiendas recomendadas:</h3>
              <div className="stores-categories">
                <div className="store-category-group">
                  <div className="store-category">
                    <span className="store-bullet">Accesibles:</span>
                  </div>
                  {result.tiendas_accesibles && result.tiendas_accesibles.length > 0 ? (
                    <div className="stores-list">
                      {result.tiendas_accesibles.map((tienda, idx) => (
                        <span key={idx} className="store-tag">{tienda}</span>
                      ))}
                    </div>
                  ) : (
                    <p>No hay tiendas accesibles disponibles</p>
                  )}
                </div>
                
                <div className="store-category-group">
                  <div className="store-category">
                    <span className="store-bullet">Lujo:</span>
                  </div>
                  {result.tiendas_lujo && result.tiendas_lujo.length > 0 ? (
                    <div className="stores-list">
                      {result.tiendas_lujo.map((tienda, idx) => (
                        <span key={idx} className="store-tag">{tienda}</span>
                      ))}
                    </div>
                  ) : (
                    <p>No hay tiendas de lujo disponibles</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="button-center">
            <button onClick={savePrediction} className="btn-save">
              Guardar predicción
            </button>
            <button onClick={resetSelection} className="btn-reset">
              Nueva predicción
            </button>
          </div>
        </div>
      )}

      {!result && (
        <div className="help-text">
          <p>Sube una imagen o escribe tu estilo para comenzar</p>
        </div>
      )}
      
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
}
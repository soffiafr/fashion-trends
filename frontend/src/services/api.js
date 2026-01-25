// src/services/api.js
const API_URL = import.meta.env.VITE_API_URL || 'https://fashion-trends-production.up.railway.app';

console.log('API_URL en api.js:', API_URL);

export const analyzeImage = async (imageData) => {
  try {
    const response = await fetch(`${API_URL}/analyze-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: imageData })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `Error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.error) errorMessage = errorJson.error;
      } catch (e) {
        // No es JSON, usar texto plano si existe
        if (errorText) errorMessage = `Error ${response.status}: ${errorText.substring(0, 100)}`;
      }
      throw new Error(errorMessage);
    }
    return response.json();
  } catch (error) {
    console.error('Detalles del error de análisis:', error);
    throw error;
  }
};

export const predictFashion = async (data) => {
  const response = await fetch(`${API_URL}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Error en predicción');
  }
  return response.json();
};

export const checkHealth = async () => {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
};
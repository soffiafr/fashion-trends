// src/services/api.js
const API_URL = import.meta.env.VITE_API_URL || 'https://fashion-trends-production.up.railway.app';

console.log('API_URL en api.js:', API_URL);

export const analyzeImage = async (imageData) => {
  const response = await fetch(`${API_URL}/analyze-image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageData })
  });
  
  if (!response.ok) throw new Error('Error al analizar imagen');
  return response.json();
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
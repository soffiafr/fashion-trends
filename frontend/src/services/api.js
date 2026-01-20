const API_URL = import.meta.env.VITE_ML_API_URL;

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
  
  if (!response.ok) throw new Error('Error en predicción');
  return response.json();
};

export const checkHealth = async () => {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
};
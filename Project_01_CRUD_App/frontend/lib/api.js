const API_URL = 'http://127.0.0.1:8000';

export async function fetchWithAuth(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // If body is URLSearchParams, remove Content-Type JSON
  const isUrlEncoded = options.body instanceof URLSearchParams;
  if (isUrlEncoded) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'API Request Failed');
  }

  return response.json();
}

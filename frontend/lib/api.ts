/**
 * Axios instance configured for the backend API.
 *
 * Centralizes:
 * - Base URL configuration
 * - Request/response interceptors
 * - Error handling
 *
 * When Docker is added, change NEXT_PUBLIC_API_URL env var.
 */

import axios, { type AxiosError, type AxiosInstance } from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor — add auth tokens here in future milestones
api.interceptors.request.use(
  (config) => {
    // Future: attach JWT or API key
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor — centralized error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      // Server responded with a status code outside 2xx
      console.error(
        `API Error: ${error.response.status} - ${error.response.statusText}`
      );
    } else if (error.request) {
      // Request was made but no response received
      console.error("API Error: No response received from backend");
    } else {
      // Something else happened
      console.error(`API Error: ${error.message}`);
    }
    return Promise.reject(error);
  }
);

export default api;

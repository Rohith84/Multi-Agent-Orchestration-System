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
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor — attach JWT token
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor — centralized error handling & 401 redirect
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      console.error(
        `API Error: ${error.response.status} - ${error.response.statusText}`
      );
      if (error.response.status === 401) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          if (!window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
          }
        }
      }
    } else if (error.request) {
      console.error("API Error: No response received from backend");
    } else {
      console.error(`API Error: ${error.message}`);
    }
    return Promise.reject(error);
  }
);

export default api;

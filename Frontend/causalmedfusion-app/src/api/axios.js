import axios from "axios";

const API = axios.create({
    baseURL: "http://localhost:8000/api/",
});


// 🔹 Attach access token to every request
API.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("access");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);


// 🔹 Handle token refresh automatically
API.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // If no response (network error)
        if (!error.response) {
            return Promise.reject(error);
        }

        // If access token expired
        if (error.response.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            const refresh = localStorage.getItem("refresh");

            if (!refresh) {
                localStorage.clear();
                alert("Session expired! Login again.");
                window.location.href = "/login";
                return Promise.reject(error);
            }

            try {
                const res = await axios.post(
                    "http://localhost:8000/api/auth/refresh/",
                    { refresh }
                );

                localStorage.setItem("access", res.data.access);

                originalRequest.headers.Authorization = `Bearer ${res.data.access}`;
                return API(originalRequest);

            } catch (refreshError) {
                localStorage.clear();
                alert("Session expired! Login again.");
                window.location.href = "/login";
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

export default API;

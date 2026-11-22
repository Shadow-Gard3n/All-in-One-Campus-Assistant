import axios from "axios";

const api = axios.create({
    baseURL: "http://127.0.0.1:8000",
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("access_token");

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        // Keep JSON for normal requests,
        // but let Axios/browser set multipart headers for FormData.
        if (!(config.data instanceof FormData)) {
            config.headers["Content-Type"] = "application/json";
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default api;

// import axios from "axios";

// const api = axios.create({
//     baseURL: "http://127.0.0.1:8000",
//     headers: {
//         "Content-Type": "application/json",
//     },
// });

// api.interceptors.request.use(
//     (config) => {
//         const token = localStorage.getItem("access_token");

//         if (token) {
//             config.headers.Authorization = `Bearer ${token}`;
//         }

//         return config;
//     },
//     (error) => {
//         return Promise.reject(error);
//     }
// );

// export default api;
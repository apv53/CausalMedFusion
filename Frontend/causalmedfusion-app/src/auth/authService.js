import axios from "axios";

const BASE_URL = "http://localhost:8000/api/auth/";

// =======================
// LOGIN
// =======================
export const login = async (username, password) => {
  const response = await axios.post(`${BASE_URL}login/`, {
    username,
    password,
  });

  const { access, refresh, user } = response.data;

  localStorage.setItem("access", access);
  localStorage.setItem("refresh", refresh);
  localStorage.setItem("user", JSON.stringify(user));

  return response.data;
};


// =======================
// SIGNUP (creates request)
// =======================
export const signup = async (
  username,
  email,
  password,
  role
) => {
  const response = await axios.post(
    `${BASE_URL}signup/`,
    {
      username,
      email,
      password,
      role,
    }
  );

  return response.data;
};


// =======================
// LOGOUT
// =======================
export const logout = () => {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  localStorage.removeItem("user");
};

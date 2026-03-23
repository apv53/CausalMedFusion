import { useEffect, useState } from "react";
import API from "../api/axios";

export default function Topbar() {
  const [username, setUsername] = useState("");

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await API.get("me/");
        setUsername(res.data.username);
      } catch (err) {
        console.error("Error fetching user:", err);
      }
    };

    fetchUser();
  }, []);

  return (
    <div className="d-flex justify-content-between align-items-center mb-4">
      <h5>Hello {username} 👋</h5>
    </div>
  );
}

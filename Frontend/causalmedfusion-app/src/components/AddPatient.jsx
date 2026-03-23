import { useState } from "react";
import API from "../api/axios";

function AddPatient() {
    const [form, setForm] = useState({
        patient_id: "",
        name: "",
        gender: "",
        age: "",
        phone: "",
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        await API.post("patients/", form);
        alert("Patient added!");
    };

    return (
        <form onSubmit={handleSubmit}>
            <input placeholder="Patient ID"
                onChange={(e) => setForm({ ...form, patient_id: e.target.value })} />

            <input placeholder="Name"
                onChange={(e) => setForm({ ...form, name: e.target.value })} />

            <input placeholder="Gender"
                onChange={(e) => setForm({ ...form, gender: e.target.value })} />

            <input placeholder="Age"
                onChange={(e) => setForm({ ...form, age: e.target.value })} />

            <input placeholder="Phone"
                onChange={(e) => setForm({ ...form, phone: e.target.value })} />

            <button type="submit">Add</button>
        </form>
    );
}

export default AddPatient;

import { useEffect, useState } from "react";
import API from "../api/axios";

export default function PendingRequests() {
    const [requests, setRequests] = useState([]);

    const fetchRequests = async () => {
        try {
            const res = await API.get("auth/pending/");
            setRequests(res.data);
        } catch (err) {
            console.error("Failed to fetch pending requests");
        }
    };

    useEffect(() => {
        fetchRequests();
    }, []);

    const handleApprove = async (id) => {
        try {
            await API.post(`auth/approve/${id}/`);
            fetchRequests();
        } catch (err) {
            alert("Approval failed");
        }
    };

    const handleReject = async (id) => {
        try {
            await API.post(`auth/reject/${id}/`);
            fetchRequests();
        } catch (err) {
            alert("Rejection failed");
        }
    };

    if (requests.length === 0) {
        return (
            <div className="card shadow-sm mt-4 p-3">
                <h6 className="fw-bold mb-3">
                    Pending Signup Requests
                </h6>
                <p className="text-muted">No pending requests.</p>
            </div>
        );
    }

    return (
        <div className="card shadow-sm mt-4">
            <div className="card-body">
                <h6 className="fw-bold mb-3">
                    Pending Signup Requests
                </h6>

                <table className="table align-middle">
                    <thead className="text-muted">
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Requested At</th>
                            <th className="text-end">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {requests.map((r) => (
                            <tr key={r.id}>
                                <td className="fw-semibold">
                                    {r.username}
                                </td>
                                <td>{r.email}</td>
                                <td>{r.role}</td>
                                <td>
                                    {new Date(
                                        r.requested_at
                                    ).toLocaleString()}
                                </td>
                                <td className="text-end">
                                    <div className="d-flex justify-content-end gap-2">
                                        <button
                                            className="btn btn-sm btn-success"
                                            onClick={() =>
                                                handleApprove(r.id)
                                            }
                                        >
                                            Approve
                                        </button>
                                        <button
                                            className="btn btn-sm btn-outline-danger"
                                            onClick={() =>
                                                handleReject(r.id)
                                            }
                                        >
                                            Reject
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

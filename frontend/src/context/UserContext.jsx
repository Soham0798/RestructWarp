import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../config';

const UserContext = createContext(null);

export const UserProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchUser = useCallback(async () => {
        const token = localStorage.getItem('token');
        if (!token) { setLoading(false); return; }
        try {
            const res = await fetch(`${API_BASE}/dashboard/me`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) { localStorage.removeItem('token'); setUser(null); }
            else setUser(await res.json());
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchUser(); }, [fetchUser]);

    return (
        <UserContext.Provider value={{ user, setUser, loading, refetch: fetchUser }}>
            {children}
        </UserContext.Provider>
    );
};

export const useUser = () => useContext(UserContext);

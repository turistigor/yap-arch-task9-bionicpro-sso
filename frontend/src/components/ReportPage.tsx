import React, { useState, useEffect } from 'react';
import { useCookies } from 'react-cookie'

import { AuthAgent, UserInfo } from './Auth';
import { UserBadge } from './UserBage';

interface AuthCookies {
    user?: UserInfo;
}

const AUTH_URL = `${process.env.REACT_APP_API_URL}`
const AUTH_PREFIX: string = '/api/v1/auth'
const AUTH_LOGIN_PATH: string = `${AUTH_PREFIX}/login`;
const AUTH_STATUS_PATH: string = `${AUTH_PREFIX}/status`;
const AUTH_LOGOUT_PATH: string = `${AUTH_PREFIX}/logout`;

const REPORTS_URL = `${process.env.REACT_APP_REPORTS_URL}`
const REPORTS_PREFIX = '/api/v1'
const GET_REPORT_PATH = `${REPORTS_PREFIX}/reports`


const ReportPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [report, setReport] = useState<string | null>(null);
    const [cookies] = useCookies<keyof AuthCookies>(['user']);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userInfo, setUserInfo] = useState<UserInfo | undefined>(undefined);
    const authAgent = new AuthAgent(
        cookies, `${AUTH_URL}${AUTH_STATUS_PATH}`, `${AUTH_URL}${AUTH_LOGOUT_PATH}`
    );

    useEffect(() => {
        const checkAuth = async () => {
            try {
                const isAuth = await authAgent.isAuthenticated();
                setIsAuthenticated(isAuth);

                if (isAuth) {
                    const userInfo = authAgent.getUserInfo();
                    setUserInfo(userInfo);
                }
            } catch (err) {
                setError('Failed to verify authentication status');
            }
        };

        checkAuth();
    }, [cookies]);

    const downloadReport = async () => {
        if (!isAuthenticated) {
            setError('Not authenticated');
            return;
        }

        setLoading(true);
        setError(null);
        let response = null;

        try {
            response = await fetch(
                `${REPORTS_URL}${GET_REPORT_PATH}`, { credentials: 'include' }
            );
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }

        if (!response) {
            return;
        }

        if (!response.ok) {
            if (response.status === 401) {
                setIsAuthenticated(false);
            } else {
                setError(`An error occurred: ${await response.text()}`)
            }
        }
        else {
            setReport(`${await response.text()}`)
        }
    };

    const handleLogin = () => {
        window.location.href = `${AUTH_URL}${AUTH_LOGIN_PATH}`;
    };

    const handleLogout = async () => {
        if (!isAuthenticated) {
            setError('Not authenticated');
            return;
        }

        const result = await authAgent.logout();
        if (result === true) {
            setError(null);
        }
        setIsAuthenticated(false);
    }

    if (!isAuthenticated) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
                <button
                    onClick={handleLogin}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                    Login
                </button>
            </div>
        );
    }

    const report_lines: string[] = report ? report.split(/\\n|\n/g) : [];
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
            <div className="p-8 bg-white rounded-lg shadow-md space-x-4">
                <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

                {userInfo && <UserBadge user={userInfo} />}

                <button
                    onClick={downloadReport}
                    disabled={loading}
                    className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${loading ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                >
                    {loading ? 'Generating Report...' : 'Download Report'}
                </button>

                {!loading && (
                    <button
                        onClick={handleLogout}
                        disabled={loading}
                        className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${loading ? 'opacity-50 cursor-not-allowed' : ''
                            }`}
                    >
                        Logout
                    </button>
                    
                )}

                {error && (
                    <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
                        {error}
                    </div>
                )}

                {!error && report && (
                    <div className="mt-4 p-4 bg-purple-100 text-purple-700 rounded whitespace-pre-wrap break-words">
                        {report_lines.map((line, index) => (
                            <p key={index} className="break-words">
                            {line}
                            </p>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ReportPage;
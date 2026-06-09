import { Cookie } from 'universal-cookie';

export interface UserInfo {
    sub: string;
    roles: string[];
    name: string;
    preferred_username: string;
    given_name: string;
    family_name: string;
    email: string;
}

export class AuthAgent {
    private _cookies: Cookie | undefined;
    private _authStatusUrl: string;
    private _logoutUrl: string;

    constructor(
        cookies: Cookie | undefined, authStatusUrl: string, logoutUrl: string,
    ){
        this._cookies = cookies;
        this._authStatusUrl = authStatusUrl;
        this._logoutUrl = logoutUrl;
    }

    public async isAuthenticated(): Promise<boolean> {
        let response = null;
        try {
            response = await fetch(this._authStatusUrl,  {credentials: 'include'});
        }
        catch (ex)
        {
            console.log(`Authentication status request network error: ${ex}`)
            return false;
        }

        if (response.status == 200) {
            return true;
        }

        if (response.status == 401) {
            return false;
        }

        return false
    }

    public async logout(): Promise<boolean> {
        let response = null;
        try {
            response = await fetch(this._logoutUrl,  {credentials: 'include'});
        }
        catch (ex)
        {
            console.log(`Logout network error: ${ex}`);
            return false;
        }

        return response.ok;
    }

    public getUserInfo(): UserInfo | undefined {
        return this._cookies.user;
    }
}
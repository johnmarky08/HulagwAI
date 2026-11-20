import { http, web } from "./client";

export const auth = {
    async me() {
        return (await http.get("/me")).data; // {authenticated,user,quota,upload,history_mode}
    },
    async login(email, password) {
        return (await web.post("/login", { email, password })).data;
    },
    async register(name, email, password, password_confirmation) {
        return (await web.post("/register", { name, email, password, password_confirmation })).data;
    },
    async logout() {
        return (await web.post("/logout")).data;
    },
    async updateProfile(name, email) {
        return (await http.put("/account/profile", { name, email })).data;
    },
    async changePassword(current_password, password, password_confirmation) {
        return (await http.put("/account/password", { current_password, password, password_confirmation })).data;
    },
    async deleteAccount(password) {
        return (await http.post("/account/delete", { password })).data;
    },
};

import { NextRequest, NextResponse } from "next/server";

// Route yang butuh login
const PROTECTED_ROUTES = ["/admin", "/ketua", "/pengawas"];

// Route yang hanya bisa diakses kalau BELUM login
const AUTH_ONLY_ROUTES  = ["/login"];

export function middleware(req: NextRequest) {
    const { pathname } = req.nextUrl;

    // Ambil token dari cookie (dikirim oleh client via js-cookie atau manual)
    const token = req.cookies.get("token")?.value;

    const isProtected = PROTECTED_ROUTES.some((r) => pathname.startsWith(r));
    const isAuthOnly  = AUTH_ONLY_ROUTES.some((r)  => pathname.startsWith(r));

    // Belum login → coba akses halaman protected → redirect ke /login
    if (isProtected && !token) {
        const loginUrl = req.nextUrl.clone();
        loginUrl.pathname = "/login";
        loginUrl.searchParams.set("from", pathname); // simpan asal redirect
        return NextResponse.redirect(loginUrl);
    }

    // Sudah login → coba akses /login → redirect ke /dashboard
    if (isAuthOnly && token) {
        const dashUrl = req.nextUrl.clone();
        dashUrl.pathname = "/dashboard";
        return NextResponse.redirect(dashUrl);
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        "/admin/:path*",
        "/ketua/:path*",
        "/pengawas/:path*",
        "/login",
    ],
};
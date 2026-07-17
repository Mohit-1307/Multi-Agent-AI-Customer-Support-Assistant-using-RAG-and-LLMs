// frontend/pages/login.js
//
// Login page. Redirects straight to /chat if the user is already
// logged in, otherwise shows an email/password form.

import { useState, useEffect } from "react";

import { useRouter } from "next/router";

import Head from "next/head";

import Link from "next/link";

import { authAPI } from "../services/api";

export default function LoginPage() {

  const router = useRouter();

  // Form field values
  const [form, setForm] = useState({ email: "", password: "" });

  // Error message shown above the submit button
  const [error, setError] = useState("");

  // True while the login request is in flight, disables the submit button
  const [loading, setLoading] = useState(false);

  // To Show/Hide Password
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {

    // If a valid session already exists, skip the login form entirely
    if (authAPI.isLoggedIn()) router.push("/chat");

  }, []);

  // Generic change handler — updates whichever field the user is typing into,
  // matched by the input's "name" attribute
  const handleChange = (e) =>

    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {

    e.preventDefault();

    setError("");

    if (!form.email || !form.password) {

      setError("Please fill in all fields.");

      return;

    }

    setLoading(true);

    try {

      await authAPI.login(form.email, form.password);

      router.push("/chat");

    } catch (err) {

      setError(err.message || "Login failed. Check your credentials.");

    } finally {

      setLoading(false);

    }

  };

  return (

    <>

      <Head>

        <title>Login — TechMart AI Support</title>

      </Head>

      <div className = "min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 px-4">

        {/* Background decorative circles */}
        <div className = "absolute inset-0 overflow-hidden pointer-events-none">

          <div className = "absolute -top-32 -right-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />

          <div className = "absolute -bottom-32 -left-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />

        </div>

        <div className = "w-full max-w-md relative">

          {/* Logo */}
          <div className = "text-center mb-8">

            <div className = "inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 text-white text-3xl font-bold mb-4 shadow-lg shadow-blue-600/30">

              T

            </div>

            <h1 className = "text-2xl font-bold text-white">

              TechMart AI Support

            </h1>

            <p className = "text-slate-400 text-sm mt-1">

              Sign in to your account

            </p>

          </div>

          {/* Card */}
          <div className = "bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">

            <form onSubmit = {handleSubmit} className = "space-y-5">

              <div>

                <label className = "block text-sm font-medium text-slate-300 mb-1.5">

                  Email Address

                </label>

                <input

                  type = "email"

                  name = "email"

                  value = {form.email}

                  onChange = {handleChange}

                  placeholder = "you@example.com"

                  className = "w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all text-sm"

                  autoComplete = "email"

                  required

                />

              </div>

              <div>

                <div className = "flex items-center justify-between mb-1.5">

                  <label className = "block text-sm font-medium text-slate-300">

                    Password

                  </label>

                </div>

                <div style = {{ position: "relative" }}>

                  <input

                    type = {showPassword ? "text" : "password"}

                    name = "password"

                    value = {form.password}

                    onChange = {handleChange}

                    placeholder="••••••••"

                    className = "w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all text-sm"

                    style = {{ paddingRight: "44px" }}

                    autoComplete = "current-password"

                    required

                  />

                  <button

                    type = "button"

                    onClick={() => setShowPassword((prev) => !prev)}

                    style={{

                      position: "absolute",

                      right: 12,

                      top: "50%",

                      transform: "translateY(-50%)",

                      background: "none",

                      border: "none",

                      cursor: "pointer",

                      color: "#64748B",

                      padding: 0,

                      display: "flex",

                      alignItems: "center"

                    }}

                  >

                    {showPassword ? (

                      <svg width = "18" height = "18" viewBox = "0 0 24 24" fill = "none" stroke = "currentColor" strokeWidth = "2" strokeLinecap = "round" strokeLinejoin = "round">

                        <path d = "M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>

                        <path d = "M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>

                        <line x1 ="1" y1 = "1" x2 = "23" y2 = "23"/>

                      </svg>

                    ) : (

                      <svg width = "18" height = "18" viewBox = "0 0 24 24" fill = "none" stroke = "currentColor" strokeWidth = "2" strokeLinecap = "round" strokeLinejoin = "round">

                        <path d = "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>

                        <circle cx = "12" cy = "12" r = "3"/>

                      </svg>

                    )}

                  </button>

                </div>

              </div>

              {error && (

                <div className = "bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm fade-in">

                  ⚠️ {error}

                </div>

              )}

              <button

                type = "submit"

                disabled = {loading}

                className = "w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-semibold py-3 rounded-xl transition-all text-sm shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2"

              >

                {loading ? (

                  <>

                    <svg

                      className = "animate-spin w-4 h-4"

                      viewBox = "0 0 24 24"

                      fill = "none"

                    >

                      <circle

                        className = "opacity-25"

                        cx = "12"

                        cy = "12"

                        r = "10"

                        stroke = "currentColor"

                        strokeWidth = "4"

                      />

                      <path

                        className = "opacity-75"

                        fill = "currentColor"

                        d = "M4 12a8 8 0 018-8v8H4z"

                      />

                    </svg>

                    Signing in...

                  </>

                ) : (

                  "Sign In"

                )}

              </button>

            </form>

            <div className = "mt-6 pt-6 border-t border-white/10 text-center">

              <p className = "text-slate-400 text-sm">

                Don't have an account?{" "}

                <Link

                  href = "/register"

                  className = "text-blue-400 hover:text-blue-300 font-medium transition-colors"

                >
                  Create one

                </Link>

              </p>

            </div>

          </div>

          {/* Demo credentials hint */}
          <div className = "mt-4 text-center">

            <p className = "text-slate-500 text-xs">

              Demo: admin@gmail.com / admin123

            </p>

          </div>

        </div>

      </div>

    </>

  );

}

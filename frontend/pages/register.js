// frontend/pages/register.js
//
// Account creation page. Validates the form client-side (name, email,
// password length/match) before calling the register API, and shows
// a simple password-strength indicator as the user types.

import { useState, useEffect } from "react";

import { useRouter } from "next/router";

import Head from "next/head";

import Link from "next/link";

import { authAPI } from "../services/api";

export default function RegisterPage() {

  const router = useRouter();

  const [form, setForm] = useState({

    name: "",

    email: "",

    phone: "",

    password: "",

    confirm: ""

  });

  const [error, setError] = useState("");

  const [loading, setLoading] = useState(false);

// To Show/Hide Password
  const [showPassword, setShowPassword] = useState(false);

// To Show/Hide Password
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {

    // Skip registration entirely if already logged in
    if (authAPI.isLoggedIn()) router.push("/chat");

  }, []);

  const handleChange = (e) =>

    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  // Client-side validation, returns an error string or null if the form is valid
  const validate = () => {

    if (!form.name.trim()) return "Please enter your name.";

    if (!form.email) return "Please enter your email.";

    if (form.password.length < 6)

      return "Password must be at least 6 characters.";

    if (form.password !== form.confirm) return "Passwords do not match.";

    return null;

  };

  const handleSubmit = async (e) => {

    e.preventDefault();

    const validationError = validate();

    if (validationError) {

      setError(validationError);

      return;

    }

    setError("");

    setLoading(true);

    try {

      await authAPI.register(

        form.name.trim(),

        form.email,

        form.password,

        form.phone || null

      );

      router.push("/chat");

    } catch (err) {

      setError(err.message || "Registration failed. Please try again.");

    } finally {

      setLoading(false);

    }

  };

  // Simple password strength score based on length only:
  // 0 = empty, 1 = weak (<6 chars), 2 = good (<10 chars), 3 = strong (10+ chars)
  const strength =

    form.password.length === 0

      ? 0

      : form.password.length < 6

        ? 1

        : form.password.length < 10

          ? 2

          : 3;

  const strengthLabel = ["", "Weak", "Good", "Strong"];

  const strengthColor = ["", "bg-red-500", "bg-yellow-500", "bg-green-500"];

  return (

    <>
      <Head>

        <title>Create Account — TechMart AI Support</title>

      </Head>

      <div className = "min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 px-4 py-8">

        <div className = "absolute inset-0 overflow-hidden pointer-events-none">

          <div className = " absolute -top-32 -right-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />

          <div className = "absolute -bottom-32 -left-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />

        </div>

        <div className = "w-full max-w-md relative">

          <div className = "text-center mb-8">

            <div className = "inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 text-white text-3xl font-bold mb-4 shadow-lg shadow-blue-600/30">

              T

            </div>

            <h1 className = "text-2xl font-bold text-white">

              Create Your Account

            </h1>

            <p className = "text-slate-400 text-sm mt-1">

              Get started with TechMart AI Support

            </p>

          </div>

          <div className = "bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">

            <form onSubmit = {handleSubmit} className = "space-y-4">

              <div>

                <label className = "block text-sm font-medium text-slate-300 mb-1.5">

                  Full Name

                </label>

                <input

                  type = "text"

                  name = "name"

                  value = {form.name}

                  onChange = {handleChange}

                  placeholder = "Jane Doe"

                  className = "w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all text-sm"

                  required

                />

              </div>

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

                <div>

                  <label className = "block text-sm font-medium text-slate-300 mb-1.5">

                    Phone Number

                    <span className = "text-slate-500 font-normal ml-1">

                      (optional — for WhatsApp alerts)

                    </span>

                  </label>

                  <input

                    type = "tel"

                    name = "phone"

                    value = {form.phone}

                    onChange = {handleChange}

                    placeholder = "+91 98765 43210"

                    className = "w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all text-sm"

                  />

                  <p className = "text-slate-500 text-xs mt-1">

                    Include country code e.g. +91 for India, +1 for US

                  </p>

                </div>

                <label className = "block text-sm font-medium text-slate-300 mb-1.5">

                  Password

                </label>

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

                {form.password && (

                  <div className = "mt-2 flex items-center gap-2">

                    <div className = "flex-1 h-1 bg-white/10 rounded-full overflow-hidden">

                      <div

                        className = {`h-full rounded-full transition-all ${strengthColor[strength]}`}

                        style = {{ width: `${(strength / 3) * 100}%` }}

                      />

                    </div>

                    <span className = "text-xs text-slate-400">

                      {strengthLabel[strength]}

                    </span>

                  </div>

                )}

              </div>

              <div>

                <label className = "block text-sm font-medium text-slate-300 mb-1.5">

                  Confirm Password

                </label>

                <div style={{ position: "relative" }}>
                  <input
                    type={showConfirm ? "text" : "password"}
                    name="confirm"
                    value={form.confirm}
                    onChange={handleChange}
                    placeholder="Repeat your password"
                    className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all text-sm"
                    style={{ paddingRight: "44px" }}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((prev) => !prev)}
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
                      alignItems: "center",
                    }}
                  >
                    {showConfirm ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                        <line x1="1" y1="1" x2="23" y2="23"/>
                      </svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    )}
                  </button>
                </div>

                {form.confirm && form.password !== form.confirm && (

                  <p className = "text-red-400 text-xs mt-1.5">

                    Passwords don't match

                  </p>

                )}

              </div>

              {error && (

                <div className = "bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm fade-in">

                  ⚠️ {error}

                </div>

              )}

              <button

                type = "submit"

                disabled = {loading}

                className = "w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-semibold py-3 rounded-xl transition-all text-sm shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2 mt-2"

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

                    Creating account...

                  </>

                ) : (

                  "Create Account"

                )}

              </button>

            </form>

            <div className = "mt-6 pt-6 border-t border-white/10 text-center">

              <p className = "text-slate-400 text-sm">

                Already have an account?{" "}

                <Link

                  href = "/login"

                  className = "text-blue-400 hover:text-blue-300 font-medium"

                >

                  Sign in
                  
                </Link>
              </p>

            </div>

          </div>

        </div>

      </div>
    </>

  );

}

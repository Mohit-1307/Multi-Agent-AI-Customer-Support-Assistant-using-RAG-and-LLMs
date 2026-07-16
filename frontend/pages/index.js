// frontend/pages/index.js
//
// The root "/" route. This page doesn't render anything itself — it just
// checks whether the visitor is logged in and redirects them to the
// appropriate page (chat if logged in, login if not).

import { useEffect } from "react";

import { useRouter } from "next/router";

import { authAPI } from "../services/api";

export default function IndexPage() {

  const router = useRouter();

  useEffect(() => {

    // Runs once, right after the component mounts on the client
    if (authAPI.isLoggedIn()) {

      router.replace("/chat");

    } 
    
    else {

      router.replace("/login");

    }

  }, []);

  // Nothing to render — this page only redirects
  return null;

}

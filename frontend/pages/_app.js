// frontend/pages/_app.js
//
// Next.js custom App component. Every page in the app gets rendered
// through this wrapper, which is why the global stylesheet is imported here.

import "../styles/globals.css";

export default function App({ Component, pageProps }) {

  // Component is whichever page is currently being rendered (chat, login, etc.),
  // and pageProps are the props Next.js passes to that page
  return <Component {...pageProps} />;

}

import Head from 'next/head';
import dynamic from 'next/dynamic';
import type { NextPage } from 'next';

// Dynamically import to avoid SSR issues with Chart.js
const EEGDashboard = dynamic(
  () => import('../components/EEGDashboard'),
  { ssr: false }
);

const Home: NextPage = () => {
  return (
    <>
      <Head>
        <title>Advanced EEG Love Detection System</title>
        <meta name="description" content="Real-time EEG analysis for love at first sight detection" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <EEGDashboard />
      </main>

      <style jsx global>{`
        * {
          box-sizing: border-box;
          padding: 0;
          margin: 0;
        }

        html,
        body {
          max-width: 100vw;
          overflow-x: hidden;
          background-color: #f9fafb;
        }

        body {
          color: #1f2937;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        a {
          color: inherit;
          text-decoration: none;
        }

        main {
          min-height: 100vh;
          padding: 20px;
        }
      `}</style>
    </>
  );
};

export default Home;
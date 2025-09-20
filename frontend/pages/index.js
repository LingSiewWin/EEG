import Head from 'next/head';
import EEGDashboard from '../components/EEGDashboard';

export default function Home() {
  return (
    <>
      <Head>
        <title>EEG Real-Time Dashboard</title>
        <meta name="description" content="Real-time EEG data visualization from OpenBCI Cyton+Daisy" />
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
}
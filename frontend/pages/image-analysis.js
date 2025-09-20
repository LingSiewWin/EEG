import Head from 'next/head';
import dynamic from 'next/dynamic';

// Dynamically import to avoid SSR issues with Chart.js
const ImageLoveAnalysis = dynamic(
  () => import('../components/ImageLoveAnalysis'),
  { ssr: false }
);

export default function ImageAnalysisPage() {
  return (
    <>
      <Head>
        <title>Image-Based Love Detection | EEG Analysis</title>
        <meta name="description" content="Analyze your EEG response to different images" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <ImageLoveAnalysis />
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
        }
      `}</style>
    </>
  );
}
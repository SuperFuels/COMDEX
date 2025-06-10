"use client"

import { useEffect, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface Props {
  url: string;
  onClose: () => void;
}

export default function PdfModal({ url, onClose }: Props) {
  const [numPages, setNumPages] = useState<number | null>(null);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex justify-center items-center z-50">
      <div className="bg-white p-6 rounded shadow-lg max-w-3xl w-full relative">
        <button
          onClick={onClose}
          className="absolute top-2 right-2 text-red-500 font-bold text-lg"
        >
          ✖
        </button>
        <h2 className="text-xl font-semibold mb-4">📄 Deal PDF Preview</h2>
        <div className="overflow-auto max-h-[75vh]">
          <Document
            file={url}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
          >
            {Array.from(new Array(numPages), (el, i) => (
              <Page key={`page_${i + 1}`} pageNumber={i + 1} />
            ))}
          </Document>
        </div>
      </div>
    </div>
  );
}


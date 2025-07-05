'use client';

import React, { useState } from 'react';
import styles from '@/styles/AIONDashboard.module.css';
import { Button } from '@/components/ui/button';

export default function AIONTerminal() {
  const [leftOutput, setLeftOutput] = useState('Left terminal output...');
  const [rightOutput, setRightOutput] = useState('');
  const [askInput, setAskInput] = useState('');
  const [loading, setLoading] = useState(false);

  const callEndpoint = async (endpoint: string) => {
    setLeftOutput(prev => prev + `\n> Calling ${endpoint}...\n`);
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const json = await res.json();
      setLeftOutput(prev => prev + JSON.stringify(json, null, 2) + '\n');
    } catch (err) {
      setLeftOutput(prev => prev + `Error: ${err}\n`);
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!askInput.trim()) return;
    setLoading(true);
    setRightOutput(prev => prev + `\n> You: ${askInput}\n`);
    try {
      const res = await fetch('/api/aion/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: askInput }),
      });
      const json = await res.json();
      setRightOutput(prev => prev + `AION: ${json.response}\n`);
    } catch (err) {
      setRightOutput(prev => prev + `Error: ${err}\n`);
    } finally {
      setAskInput('');
      setLoading(false);
    }
  };

  return (
    <>
      {/* Visible output injected directly into the two terminals */}
      <script
        dangerouslySetInnerHTML={{
          __html: `
            document.getElementById("aion-left-terminal")?.replaceChildren(document.createTextNode(${JSON.stringify(leftOutput)}));
            document.getElementById("aion-right-terminal")?.replaceChildren(document.createTextNode(${JSON.stringify(rightOutput)}));
          `,
        }}
      />

      <div className={styles.footerTerminal}>
        {/* Buttons for left terminal */}
        <div className={styles.footerLeft}>
          <Button onClick={() => callEndpoint('status')}>Status</Button>
          <Button onClick={() => callEndpoint('goal')}>Goal</Button>
          <Button onClick={() => callEndpoint('identity')}>Identity</Button>
          <Button onClick={() => callEndpoint('situation')}>Situation</Button>
          <Button onClick={() => callEndpoint('boot-skill')}>Boot Skill</Button>
          <Button onClick={() => callEndpoint('skill-reflect')}>Skill Reflect</Button>
          <Button onClick={() => callEndpoint('run-dream')}>Run Dream</Button>
        </div>

        {/* Ask form for right terminal */}
        <form className={styles.askForm} onSubmit={handleAsk}>
          <input
            className={styles.askInput}
            value={askInput}
            onChange={e => setAskInput(e.target.value)}
            placeholder="Ask AION something..."
          />
          <Button type="submit" disabled={loading}>
            {loading ? '...' : 'Ask'}
          </Button>
        </form>
      </div>
    </>
  );
}
import React from 'react';

const REPO = 'https://github.com/Nikhil8557/ooda-aegis';

export const HackathonModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink" onClick={onClose}>
      <div className="bg-deep rounded-md max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 pt-6 pb-2 flex items-start justify-between gap-4 sticky top-0 bg-deep">
          <div>
            <h2 className="font-display text-2xl text-fog">How OODA-Aegis works</h2>
            <p className="text-sm text-mist">By Nikhil Kumar for the Meta Global AI Developer Hackathon 2026</p>
          </div>
          <button onClick={onClose} className="px-4 py-1.5 rounded-sm bg-raise text-fog hover:bg-slate text-sm cursor-pointer">
            Close
          </button>
        </div>
        <div className="px-6 pb-6 pt-4 space-y-6 text-sm text-mist leading-relaxed">
          <section>
            <h3 className="text-base font-semibold text-fog mb-2">The problem</h3>
            <p>
              When an exploit starts working at 3 a.m., hours pass between &ldquo;we are leaking data&rdquo; and &ldquo;a reviewed
              fix is in production&rdquo;. OODA-Aegis closes that gap on its own and never ships a fix it cannot prove.
            </p>
          </section>
          <section>
            <h3 className="text-base font-semibold text-fog mb-2">The loop</h3>
            <ol className="list-decimal pl-5 space-y-2">
              <li><span className="text-fog font-semibold">Observe.</span> Every response from the service goes to the agent. Plain rules flag leaked files, other tenants' rows, stalls and crashes.</li>
              <li><span className="text-fog font-semibold">Contain in seconds.</span> A small Meta model names the attack and writes a blocking rule in a small safe language. The agent compiles it, proves it blocks the attack and no recorded legitimate request, loads it into Nginx and sends it to peer nodes.</li>
              <li><span className="text-fog font-semibold">Red team.</span> The model invents ways around the rule, and mutation rules add more. The rule usually misses some, so the code itself has to change.</li>
              <li><span className="text-fog font-semibold">Fix and prove.</span> A larger Meta model states the rule the code must enforce and rewrites the handler. In a sandbox with no network, the real exploit must work on the old code and fail on the new one, every variant must come back safe, and legitimate requests must return exactly what they did before. Up to six candidates, each failure fed back.</li>
              <li><span className="text-fog font-semibold">Ship.</span> The new image takes 10%, 50%, then 100% of traffic with probes in between. Any failure rolls back. Then the original exploit is replayed.</li>
            </ol>
          </section>
          <section>
            <h3 className="text-base font-semibold text-fog mb-2">Meta models</h3>
            <ul className="list-disc pl-5 space-y-2">
              <li><span className="text-fog">Llama 3.2 3B</span>, open weights on the laptop through Ollama: triage, virtual patch, red team.</li>
              <li><span className="text-fog">Llama 3.1 8B</span>, open weights on the laptop: code repair in the live demo.</li>
              <li><span className="text-fog">Muse Glimmer 30B</span>, Meta's 4-bit weights on two free Kaggle T4 GPUs through llama.cpp: benchmarked on the same tasks with the same verifier. Set <code className="font-mono text-fog">GLIMMER_BASE_URL</code> to use it live.</li>
              <li><span className="text-fog">Muse Spark 1.3</span>, Meta Model API: used for repair when <code className="font-mono text-fog">MODEL_API_KEY</code> is set.</li>
            </ul>
          </section>
          <section>
            <h3 className="text-base font-semibold text-fog mb-2">What is real</h3>
            <p>
              In live mode, everything: the vulnerable FastAPI service, the leaks, Nginx, Redis, the Docker sandbox, the image
              builds, the traffic shifts and every model call. The website plays back a recorded live run, because a static page
              cannot run Docker. The customer data and the leaked secrets are fake.
            </p>
          </section>
          <a href={REPO} target="_blank" rel="noreferrer" className="inline-block px-4 py-2 rounded-sm bg-fog text-ink font-semibold hover:bg-mist">
            Code, setup and benchmark on GitHub
          </a>
        </div>
      </div>
    </div>
  );
};

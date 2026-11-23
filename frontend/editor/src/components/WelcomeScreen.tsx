/** Website-inspired entry, kept separate from caption playback behavior. */
import { Icon } from "@/lib/icons";

export function WelcomeScreen({ onNew, onOpen, onImport,onGuide }: {
  onGuide:()=>void;
  onNew: () => void;
  onOpen: () => void;
  onImport: () => void;
}) {
  return (
    <div className="welcome-site">
      <aside className="welcome-nav">
        <div className="site-mark" aria-label="Automated CWI editor"><span>CI</span></div>
        <p className="welcome-nav-title">Automated<br />Caption With Intention</p>
        <nav aria-label="Start navigation">
          <button onClick={onGuide}>Editor guide <span aria-hidden="true">→</span></button>
          <button onClick={onOpen}>The editor <span aria-hidden="true">→</span></button>
          <a href="https://captionwithintention.org" target="_blank" rel="noreferrer">The design system <span aria-hidden="true">↗</span></a>
        </nav>
        <p className="welcome-version">AUTOMATION BY LOKESH MAJHI<br />VERSION 2.0</p>
      </aside>
      <main className="welcome-main">
        <div className="welcome-intro">
          <h1>Caption with<br /><span>intention.</span></h1>
          <p className="welcome-description">Who is speaking. When it is spoken.<br />How it is said.</p>
          <p className="welcome-detail">Turn speech into editable captions, then refine the timing, attribution and type. Built to automate the Caption With Intention design system.</p>
          <div className="welcome-actions">
            <button className="primary" onClick={onOpen}>Open editor <span aria-hidden="true">→</span></button>
            <button className="ghost" onClick={onImport}>Open project JSON</button>
            <button className="ghost" onClick={onNew}><Icon name="plus" size={16} /> New project</button>
          </div>
        </div>
        <div className="welcome-specimen" aria-label="Caption typography specimen">
          <div className="specimen-rule" />
          <p><span>Every word.</span><br />With intention.</p>
          <div className="specimen-label"><span>Attribution</span><span>Synchronization</span><span>Intonation</span></div>
        </div>
        <footer className="welcome-credit">Caption With Intention is the original creators' design system. This independent editor automates it.</footer>
      </main>
    </div>
  );
}

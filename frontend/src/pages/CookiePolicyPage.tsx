import { Helmet } from 'react-helmet-async';

export function CookiePolicyPage() {
  return (
    <>
      <Helmet>
        <title>Cookie Policy - Scripe</title>
      </Helmet>

      <div className="py-12 px-4 max-w-3xl mx-auto prose prose-gray">
        <h1>Cookie Policy</h1>
        <p className="text-sm text-gray-500">Ultimo aggiornamento: Febbraio 2026</p>

        <h2>1. Cosa sono i cookie</h2>
        <p>
          I cookie sono piccoli file di testo che vengono memorizzati sul tuo
          dispositivo quando visiti un sito web. Vengono utilizzati per far
          funzionare il sito in modo efficiente e per fornire informazioni
          ai proprietari del sito.
        </p>

        <h2>2. Cookie che utilizziamo</h2>

        <h3>Cookie tecnici (necessari)</h3>
        <p>
          Questi cookie sono essenziali per il funzionamento della piattaforma
          e non possono essere disattivati.
        </p>
        <ul>
          <li>
            <strong>scripe_token</strong> - Token di autenticazione per
            mantenere la sessione attiva (localStorage)
          </li>
        </ul>

        <h3>Cookie di Cloudflare</h3>
        <p>
          Utilizziamo Cloudflare per la sicurezza e le prestazioni del sito.
          Cloudflare può impostare cookie tecnici necessari per il suo
          funzionamento.
        </p>

        <h2>3. Cookie di terze parti</h2>
        <p>
          Non utilizziamo cookie di tracciamento, cookie pubblicitari o
          cookie di analisi di terze parti. Non condividiamo dati di
          navigazione con reti pubblicitarie.
        </p>

        <h2>4. Come gestire i cookie</h2>
        <p>
          Puoi gestire i cookie tramite le impostazioni del tuo browser.
          Tieni presente che disabilitare i cookie tecnici potrebbe impedire
          il corretto funzionamento della piattaforma, in particolare
          l'autenticazione.
        </p>

        <h2>5. Contatti</h2>
        <p>
          Per domande sulla nostra cookie policy: privacy@scripe.fabioprivato.org
        </p>
      </div>
    </>
  );
}

import { Helmet } from 'react-helmet-async';

export function TermsPage() {
  return (
    <>
      <Helmet>
        <title>Termini di Servizio - Scripe</title>
      </Helmet>

      <div className="py-12 px-4 max-w-3xl mx-auto prose prose-gray">
        <h1>Termini di Servizio</h1>
        <p className="text-sm text-gray-500">Ultimo aggiornamento: Febbraio 2026</p>

        <h2>1. Accettazione dei termini</h2>
        <p>
          Utilizzando Scripe ("il Servizio"), accetti i presenti Termini di
          Servizio. Se non accetti questi termini, non utilizzare il Servizio.
        </p>

        <h2>2. Descrizione del servizio</h2>
        <p>
          Scripe è una piattaforma di lead generation B2B che raccoglie dati
          aziendali pubblicamente disponibili da fonti online. Il Servizio
          fornisce contatti aziendali verificati tramite un sistema a crediti.
        </p>

        <h2>3. Account utente</h2>
        <ul>
          <li>Devi fornire informazioni accurate durante la registrazione</li>
          <li>Sei responsabile della sicurezza del tuo account</li>
          <li>Un account è personale e non trasferibile</li>
          <li>Devi avere almeno 18 anni per utilizzare il Servizio</li>
        </ul>

        <h2>4. Sistema a crediti</h2>
        <ul>
          <li>I crediti vengono acquistati tramite i pacchetti disponibili</li>
          <li>Ogni ricerca consuma crediti in base al livello di qualità scelto</li>
          <li>I crediti acquistati non scadono</li>
          <li>I crediti non sono rimborsabili, salvo quanto previsto dalla legge</li>
          <li>I nuovi utenti ricevono 10 crediti gratuiti di benvenuto</li>
        </ul>

        <h2>5. Uso consentito</h2>
        <p>Ti impegni a utilizzare il Servizio solo per:</p>
        <ul>
          <li>Ricerca di contatti aziendali per finalità B2B legittime</li>
          <li>Comunicazioni commerciali conformi alla normativa vigente</li>
        </ul>
        <p>È vietato:</p>
        <ul>
          <li>Utilizzare i dati per spam o comunicazioni non richieste a privati</li>
          <li>Rivendere i dati ottenuti senza autorizzazione</li>
          <li>Tentare di accedere al sistema in modo non autorizzato</li>
          <li>Utilizzare il Servizio per attività illegali</li>
        </ul>

        <h2>6. Rimborsi</h2>
        <p>
          Puoi richiedere un rimborso dei crediti non utilizzati entro 14 giorni
          dall'acquisto, in conformità con il diritto di recesso previsto dal
          Codice del Consumo. I crediti già utilizzati non sono rimborsabili.
        </p>

        <h2>7. Limitazione di responsabilità</h2>
        <p>
          Scripe fornisce dati raccolti da fonti pubbliche con la massima
          diligenza possibile, ma non garantisce la completezza o l'accuratezza
          al 100% dei dati forniti. Il Servizio è fornito "così com'è".
        </p>

        <h2>8. Proprietà intellettuale</h2>
        <p>
          La piattaforma Scripe, il suo codice, design e contenuti sono
          protetti da diritto d'autore. I dati aziendali forniti possono
          essere utilizzati dall'utente per le proprie attività commerciali.
        </p>

        <h2>9. Modifiche ai termini</h2>
        <p>
          Ci riserviamo il diritto di modificare questi termini. Le modifiche
          saranno comunicate via email o tramite avviso sulla piattaforma.
          L'uso continuato del Servizio dopo le modifiche costituisce
          accettazione dei nuovi termini.
        </p>

        <h2>10. Legge applicabile</h2>
        <p>
          I presenti termini sono regolati dalla legge italiana. Per qualsiasi
          controversia è competente il Foro di residenza del consumatore.
        </p>

        <h2>11. Contatti</h2>
        <p>
          Per domande sui presenti termini: info@scripe.fabioprivato.org
        </p>
      </div>
    </>
  );
}

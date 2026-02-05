import { Helmet } from 'react-helmet-async';

export function PrivacyPage() {
  return (
    <>
      <Helmet>
        <title>Privacy Policy - Scripe</title>
      </Helmet>

      <div className="py-12 px-4 max-w-3xl mx-auto prose prose-gray">
        <h1>Privacy Policy</h1>
        <p className="text-sm text-gray-500">Ultimo aggiornamento: Febbraio 2026</p>

        <h2>1. Titolare del trattamento</h2>
        <p>
          Scripe ("noi", "nostro") si impegna a proteggere la tua privacy.
          Questa informativa descrive come raccogliamo, utilizziamo e proteggiamo
          i tuoi dati personali in conformità al Regolamento Generale sulla
          Protezione dei Dati (GDPR - Regolamento UE 2016/679).
        </p>

        <h2>2. Dati che raccogliamo</h2>
        <h3>Dati forniti dall'utente</h3>
        <ul>
          <li>Indirizzo email e nome (registrazione account)</li>
          <li>Dati di fatturazione (elaborati tramite Stripe)</li>
          <li>Query di ricerca e preferenze di utilizzo</li>
        </ul>
        <h3>Dati raccolti automaticamente</h3>
        <ul>
          <li>Indirizzo IP e dati tecnici del browser</li>
          <li>Log di accesso e utilizzo della piattaforma</li>
          <li>Cookie tecnici necessari al funzionamento</li>
        </ul>

        <h2>3. Finalità del trattamento</h2>
        <ul>
          <li>Erogazione del servizio di lead generation B2B</li>
          <li>Gestione dell'account e dei crediti</li>
          <li>Elaborazione dei pagamenti</li>
          <li>Comunicazioni relative al servizio</li>
          <li>Miglioramento della piattaforma</li>
        </ul>

        <h2>4. Base giuridica</h2>
        <p>
          Trattiamo i tuoi dati sulla base di: esecuzione del contratto
          (erogazione del servizio), consenso (per comunicazioni marketing),
          legittimo interesse (miglioramento del servizio e sicurezza),
          obbligo legale (conservazione dati fiscali).
        </p>

        <h2>5. Dati aziendali raccolti dal servizio</h2>
        <p>
          Scripe raccoglie esclusivamente dati aziendali pubblicamente disponibili
          (ragione sociale, telefono aziendale, email aziendale, indirizzo sede,
          sito web) da fonti pubbliche come Google, Bing e directory aziendali.
          Non raccogliamo dati personali di individui privati.
        </p>

        <h2>6. Condivisione dei dati</h2>
        <p>I tuoi dati non vengono venduti a terzi. Condividiamo dati solo con:</p>
        <ul>
          <li>Stripe (elaborazione pagamenti)</li>
          <li>Provider di hosting (infrastruttura tecnica)</li>
          <li>Autorità competenti (se richiesto per legge)</li>
        </ul>

        <h2>7. Conservazione dei dati</h2>
        <p>
          Conserviamo i dati del tuo account per la durata del rapporto
          contrattuale e per i periodi previsti dalla legge (es. obblighi
          fiscali). I risultati delle ricerche vengono conservati nel tuo
          account fino a cancellazione.
        </p>

        <h2>8. I tuoi diritti</h2>
        <p>Ai sensi del GDPR, hai diritto a:</p>
        <ul>
          <li>Accesso ai tuoi dati personali</li>
          <li>Rettifica dei dati inesatti</li>
          <li>Cancellazione dei dati ("diritto all'oblio")</li>
          <li>Limitazione del trattamento</li>
          <li>Portabilità dei dati</li>
          <li>Opposizione al trattamento</li>
        </ul>
        <p>
          Per esercitare i tuoi diritti, contattaci all'indirizzo email
          indicato nella sezione contatti.
        </p>

        <h2>9. Sicurezza</h2>
        <p>
          Adottiamo misure tecniche e organizzative appropriate per proteggere
          i tuoi dati, tra cui crittografia in transito (HTTPS), hashing delle
          password e controllo degli accessi.
        </p>

        <h2>10. Contatti</h2>
        <p>
          Per domande sulla privacy o per esercitare i tuoi diritti, contattaci
          all'indirizzo: privacy@scripe.fabioprivato.org
        </p>
      </div>
    </>
  );
}

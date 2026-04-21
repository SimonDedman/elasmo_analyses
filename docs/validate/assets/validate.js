/**
 * validate.js — Validation UI main logic
 *
 * Expects window.PAGE_DATA to be set before this script loads.
 * Exposes window.validateUI = { getState(), getPageData() } for submit.js.
 *
 * No ES6 modules; IIFE; var for broad compatibility.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // i18n — user-facing warnings, badges, progress text, submit button labels
  //
  // Detection: navigator.language (e.g. "es-ES" → "es"). English fallback.
  // Placeholders in strings use {name} syntax.
  // To add a language: add a new key to _I18N_STRINGS with the 12 message keys.
  // ---------------------------------------------------------------------------

  var _lang = (navigator.language || navigator.userLanguage || 'en')
              .toLowerCase().split('-')[0];

  var _I18N_STRINGS = {
    en: {
      submit_no_reviews:     'Please review at least one paper before submitting.',
      submit_no_endpoint:    'No submission endpoint is configured for this page.\nYour validation data will be downloaded as a JSON file.\nPlease e-mail it to the study coordinator.',
      submit_success:        'Validation submitted successfully. Thank you!',
      submit_failed:         'Submission failed (HTTP {status}).\nYour data will be downloaded as a JSON file.\nPlease e-mail it to the study coordinator.',
      submit_network_error:  'A network error occurred during submission.\nYour data will be downloaded as a JSON file.\nPlease e-mail it to the study coordinator.',
      submitting:            'Submitting\u2026',
      submit_btn:            'Submit',
      submitted_check:       'Submitted \u2713',
      reviewed:              'Reviewed',
      pending:               'Pending',
      progress:              '{reviewed} of {total} reviewed',
      author_not_in_db:      '"{name}" ({id}) is not yet in our database.\n\nTo be included, please ensure your papers are listed on Shark References (https://www.shark-references.com) and contact the project team.'
    },
    es: {
      submit_no_reviews:     'Por favor, revise al menos un art\u00edculo antes de enviar.',
      submit_no_endpoint:    'No hay un punto de env\u00edo configurado para esta p\u00e1gina.\nSus datos de validaci\u00f3n se descargar\u00e1n como un archivo JSON.\nPor favor, env\u00edelo por correo electr\u00f3nico al coordinador del estudio.',
      submit_success:        'Validaci\u00f3n enviada correctamente. \u00a1Gracias!',
      submit_failed:         'Error al enviar (HTTP {status}).\nSus datos se descargar\u00e1n como un archivo JSON.\nPor favor, env\u00edelo por correo electr\u00f3nico al coordinador del estudio.',
      submit_network_error:  'Se produjo un error de red durante el env\u00edo.\nSus datos se descargar\u00e1n como un archivo JSON.\nPor favor, env\u00edelo por correo electr\u00f3nico al coordinador del estudio.',
      submitting:            'Enviando\u2026',
      submit_btn:            'Enviar',
      submitted_check:       'Enviado \u2713',
      reviewed:              'Revisado',
      pending:               'Pendiente',
      progress:              '{reviewed} de {total} revisados',
      author_not_in_db:      '"{name}" ({id}) a\u00fan no est\u00e1 en nuestra base de datos.\n\nPara ser incluido, aseg\u00farese de que sus art\u00edculos est\u00e9n listados en Shark References (https://www.shark-references.com) y contacte al equipo del proyecto.'
    },
    fr: {
      submit_no_reviews:     'Veuillez examiner au moins un article avant de soumettre.',
      submit_no_endpoint:    'Aucun point de soumission n\'est configur\u00e9 pour cette page.\nVos donn\u00e9es de validation seront t\u00e9l\u00e9charg\u00e9es sous forme de fichier JSON.\nVeuillez l\'envoyer par e-mail au coordinateur de l\'\u00e9tude.',
      submit_success:        'Validation soumise avec succ\u00e8s. Merci !',
      submit_failed:         'Échec de la soumission (HTTP {status}).\nVos donn\u00e9es seront t\u00e9l\u00e9charg\u00e9es sous forme de fichier JSON.\nVeuillez l\'envoyer par e-mail au coordinateur de l\'\u00e9tude.',
      submit_network_error:  'Une erreur r\u00e9seau s\'est produite lors de la soumission.\nVos donn\u00e9es seront t\u00e9l\u00e9charg\u00e9es sous forme de fichier JSON.\nVeuillez l\'envoyer par e-mail au coordinateur de l\'\u00e9tude.',
      submitting:            'Soumission\u2026',
      submit_btn:            'Soumettre',
      submitted_check:       'Soumis \u2713',
      reviewed:              'Examin\u00e9',
      pending:               'En attente',
      progress:              '{reviewed} sur {total} examin\u00e9s',
      author_not_in_db:      '« {name} » ({id}) n\'est pas encore dans notre base de donn\u00e9es.\n\nPour y \u00eatre inclus, veuillez vous assurer que vos articles sont r\u00e9pertori\u00e9s sur Shark References (https://www.shark-references.com) et contactez l\'\u00e9quipe du projet.'
    },
    de: {
      submit_no_reviews:     'Bitte \u00fcberpr\u00fcfen Sie mindestens eine Arbeit, bevor Sie einreichen.',
      submit_no_endpoint:    'F\u00fcr diese Seite ist kein Einreichungs-Endpunkt konfiguriert.\nIhre Validierungsdaten werden als JSON-Datei heruntergeladen.\nBitte senden Sie sie per E-Mail an den Studienkoordinator.',
      submit_success:        'Validierung erfolgreich \u00fcbermittelt. Vielen Dank!',
      submit_failed:         '\u00dcbermittlung fehlgeschlagen (HTTP {status}).\nIhre Daten werden als JSON-Datei heruntergeladen.\nBitte senden Sie sie per E-Mail an den Studienkoordinator.',
      submit_network_error:  'W\u00e4hrend der \u00dcbermittlung ist ein Netzwerkfehler aufgetreten.\nIhre Daten werden als JSON-Datei heruntergeladen.\nBitte senden Sie sie per E-Mail an den Studienkoordinator.',
      submitting:            'Wird \u00fcbermittelt\u2026',
      submit_btn:            'Einreichen',
      submitted_check:       'Eingereicht \u2713',
      reviewed:              '\u00dcberpr\u00fcft',
      pending:               'Ausstehend',
      progress:              '{reviewed} von {total} \u00fcberpr\u00fcft',
      author_not_in_db:      '\u201e{name}\u201c ({id}) ist noch nicht in unserer Datenbank.\n\nUm aufgenommen zu werden, stellen Sie bitte sicher, dass Ihre Arbeiten auf Shark References (https://www.shark-references.com) gelistet sind, und kontaktieren Sie das Projektteam.'
    },
    it: {
      submit_no_reviews:     'Si prega di rivedere almeno un articolo prima dell\'invio.',
      submit_no_endpoint:    'Nessun endpoint di invio \u00e8 configurato per questa pagina.\nI dati di convalida saranno scaricati come file JSON.\nInvialo via e-mail al coordinatore dello studio.',
      submit_success:        'Convalida inviata con successo. Grazie!',
      submit_failed:         'Invio fallito (HTTP {status}).\nI dati saranno scaricati come file JSON.\nInvialo via e-mail al coordinatore dello studio.',
      submit_network_error:  'Si \u00e8 verificato un errore di rete durante l\'invio.\nI dati saranno scaricati come file JSON.\nInvialo via e-mail al coordinatore dello studio.',
      submitting:            'Invio in corso\u2026',
      submit_btn:            'Invia',
      submitted_check:       'Inviato \u2713',
      reviewed:              'Revisionato',
      pending:               'In attesa',
      progress:              '{reviewed} di {total} revisionati',
      author_not_in_db:      '"{name}" ({id}) non \u00e8 ancora nel nostro database.\n\nPer essere incluso, assicurati che i tuoi articoli siano elencati su Shark References (https://www.shark-references.com) e contatta il team del progetto.'
    },
    pt: {
      submit_no_reviews:     'Por favor, revise pelo menos um artigo antes de enviar.',
      submit_no_endpoint:    'Nenhum endpoint de envio est\u00e1 configurado para esta p\u00e1gina.\nSeus dados de valida\u00e7\u00e3o ser\u00e3o baixados como um arquivo JSON.\nPor favor, envie-o por e-mail ao coordenador do estudo.',
      submit_success:        'Valida\u00e7\u00e3o enviada com sucesso. Obrigado!',
      submit_failed:         'Falha no envio (HTTP {status}).\nSeus dados ser\u00e3o baixados como um arquivo JSON.\nPor favor, envie-o por e-mail ao coordenador do estudo.',
      submit_network_error:  'Ocorreu um erro de rede durante o envio.\nSeus dados ser\u00e3o baixados como um arquivo JSON.\nPor favor, envie-o por e-mail ao coordenador do estudo.',
      submitting:            'Enviando\u2026',
      submit_btn:            'Enviar',
      submitted_check:       'Enviado \u2713',
      reviewed:              'Revisado',
      pending:               'Pendente',
      progress:              '{reviewed} de {total} revisados',
      author_not_in_db:      '"{name}" ({id}) ainda n\u00e3o est\u00e1 em nosso banco de dados.\n\nPara ser inclu\u00eddo, certifique-se de que seus artigos estejam listados no Shark References (https://www.shark-references.com) e entre em contato com a equipe do projeto.'
    },
    nl: {
      submit_no_reviews:     'Controleer ten minste \u00e9\u00e9n paper voordat u verzendt.',
      submit_no_endpoint:    'Er is geen inzendings-eindpunt geconfigureerd voor deze pagina.\nUw validatiegegevens worden gedownload als JSON-bestand.\nStuur het per e-mail naar de studieco\u00f6rdinator.',
      submit_success:        'Validatie succesvol ingediend. Bedankt!',
      submit_failed:         'Indiening mislukt (HTTP {status}).\nUw gegevens worden gedownload als JSON-bestand.\nStuur het per e-mail naar de studieco\u00f6rdinator.',
      submit_network_error:  'Er is een netwerkfout opgetreden tijdens het indienen.\nUw gegevens worden gedownload als JSON-bestand.\nStuur het per e-mail naar de studieco\u00f6rdinator.',
      submitting:            'Bezig met verzenden\u2026',
      submit_btn:            'Verzenden',
      submitted_check:       'Verzonden \u2713',
      reviewed:              'Beoordeeld',
      pending:               'In behandeling',
      progress:              '{reviewed} van {total} beoordeeld',
      author_not_in_db:      '"{name}" ({id}) staat nog niet in onze database.\n\nOm te worden opgenomen, zorg ervoor dat uw artikelen vermeld staan op Shark References (https://www.shark-references.com) en neem contact op met het projectteam.'
    },
    pl: {
      submit_no_reviews:     'Prosz\u0119 sprawdzi\u0107 co najmniej jedn\u0105 prac\u0119 przed wys\u0142aniem.',
      submit_no_endpoint:    'Nie skonfigurowano punktu ko\u0144cowego wysy\u0142ania dla tej strony.\nTwoje dane walidacyjne zostan\u0105 pobrane jako plik JSON.\nProsz\u0119 wys\u0142a\u0107 je e-mailem do koordynatora badania.',
      submit_success:        'Walidacja zosta\u0142a pomy\u015blnie przes\u0142ana. Dzi\u0119kujemy!',
      submit_failed:         'Wysy\u0142anie nie powiod\u0142o si\u0119 (HTTP {status}).\nTwoje dane zostan\u0105 pobrane jako plik JSON.\nProsz\u0119 wys\u0142a\u0107 je e-mailem do koordynatora badania.',
      submit_network_error:  'Podczas wysy\u0142ania wyst\u0105pi\u0142 b\u0142\u0105d sieci.\nTwoje dane zostan\u0105 pobrane jako plik JSON.\nProsz\u0119 wys\u0142a\u0107 je e-mailem do koordynatora badania.',
      submitting:            'Wysy\u0142anie\u2026',
      submit_btn:            'Wy\u015blij',
      submitted_check:       'Wys\u0142ano \u2713',
      reviewed:              'Sprawdzone',
      pending:               'Oczekuj\u0105ce',
      progress:              '{reviewed} z {total} sprawdzonych',
      author_not_in_db:      '"{name}" ({id}) nie znajduje si\u0119 jeszcze w naszej bazie danych.\n\nAby zosta\u0107 uwzgl\u0119dnionym, upewnij si\u0119, \u017ce Twoje prace s\u0105 wymienione w Shark References (https://www.shark-references.com), i skontaktuj si\u0119 z zespo\u0142em projektu.'
    },
    cs: {
      submit_no_reviews:     'P\u0159ed odesl\u00e1n\u00edm pros\u00edm zkontrolujte alespo\u0148 jednu pr\u00e1ci.',
      submit_no_endpoint:    'Pro tuto str\u00e1nku nen\u00ed nakonfigurov\u00e1n \u017e\u00e1dn\u00fd endpoint pro odesl\u00e1n\u00ed.\nVa\u0161e valida\u010dn\u00ed data budou sta\u017eena jako soubor JSON.\nPros\u00edm za\u0161lete jej e-mailem koordin\u00e1torovi studie.',
      submit_success:        'Validace byla \u00fasp\u011b\u0161n\u011b odesl\u00e1na. D\u011bkujeme!',
      submit_failed:         'Odesl\u00e1n\u00ed selhalo (HTTP {status}).\nVa\u0161e data budou sta\u017eena jako soubor JSON.\nPros\u00edm za\u0161lete jej e-mailem koordin\u00e1torovi studie.',
      submit_network_error:  'P\u0159i odes\u00edl\u00e1n\u00ed do\u0161lo k chyb\u011b s\u00edt\u011b.\nVa\u0161e data budou sta\u017eena jako soubor JSON.\nPros\u00edm za\u0161lete jej e-mailem koordin\u00e1torovi studie.',
      submitting:            'Odes\u00edl\u00e1n\u00ed\u2026',
      submit_btn:            'Odeslat',
      submitted_check:       'Odesl\u00e1no \u2713',
      reviewed:              'Zkontrolov\u00e1no',
      pending:               '\u010cek\u00e1 na zpracov\u00e1n\u00ed',
      progress:              '{reviewed} z {total} zkontrolov\u00e1no',
      author_not_in_db:      '"{name}" ({id}) zat\u00edm nen\u00ed v na\u0161\u00ed datab\u00e1zi.\n\nPro za\u0159azen\u00ed se pros\u00edm uji\u0161t\u011bte, \u017ee va\u0161e pr\u00e1ce jsou uvedeny v Shark References (https://www.shark-references.com), a kontaktujte projektov\u00fd t\u00fdm.'
    },
    hu: {
      submit_no_reviews:     'K\u00e9rj\u00fck, bek\u00fcld\u00e9s el\u0151tt ellen\u0151rizzen legal\u00e1bb egy cikket.',
      submit_no_endpoint:    'Ehhez az oldalhoz nincs bek\u00fcld\u00e9si v\u00e9gpont konfigur\u00e1lva.\nAz \u00e9rv\u00e9nyes\u00edt\u00e9si adatok JSON-f\u00e1jlk\u00e9nt ker\u00fclnek let\u00f6lt\u00e9sre.\nK\u00e9rj\u00fck, k\u00fcldje el e-mailben a tanulm\u00e1ny koordin\u00e1tor\u00e1nak.',
      submit_success:        'Az \u00e9rv\u00e9nyes\u00edt\u00e9st sikeresen bek\u00fcld\u00f6tte. K\u00f6sz\u00f6nj\u00fck!',
      submit_failed:         'A bek\u00fcld\u00e9s nem siker\u00fclt (HTTP {status}).\nAz adatok JSON-f\u00e1jlk\u00e9nt ker\u00fclnek let\u00f6lt\u00e9sre.\nK\u00e9rj\u00fck, k\u00fcldje el e-mailben a tanulm\u00e1ny koordin\u00e1tor\u00e1nak.',
      submit_network_error:  'H\u00e1l\u00f3zati hiba t\u00f6rt\u00e9nt a bek\u00fcld\u00e9s sor\u00e1n.\nAz adatok JSON-f\u00e1jlk\u00e9nt ker\u00fclnek let\u00f6lt\u00e9sre.\nK\u00e9rj\u00fck, k\u00fcldje el e-mailben a tanulm\u00e1ny koordin\u00e1tor\u00e1nak.',
      submitting:            'Bek\u00fcld\u00e9s\u2026',
      submit_btn:            'Bek\u00fcld\u00e9s',
      submitted_check:       'Bek\u00fcldve \u2713',
      reviewed:              'Ellen\u0151rizve',
      pending:               'F\u00fcgg\u0151ben',
      progress:              '{reviewed} / {total} ellen\u0151rizve',
      author_not_in_db:      'A(z) "{name}" ({id}) m\u00e9g nincs az adatb\u00e1zisunkban.\n\nA beker\u00fcl\u00e9shez k\u00e9rj\u00fck, gy\u0151z\u0151dj\u00f6n meg arr\u00f3l, hogy a cikkei szerepelnek a Shark References oldalon (https://www.shark-references.com), \u00e9s l\u00e9pjen kapcsolatba a projektcsapattal.'
    },
    ro: {
      submit_no_reviews:     'V\u0103 rug\u0103m s\u0103 revizui\u021bi cel pu\u021bin o lucrare \u00eenainte de trimitere.',
      submit_no_endpoint:    'Niciun punct final de trimitere nu este configurat pentru aceast\u0103 pagin\u0103.\nDatele dvs. de validare vor fi desc\u0103rcate ca fi\u0219ier JSON.\nV\u0103 rug\u0103m s\u0103 le trimite\u021bi prin e-mail coordonatorului de studiu.',
      submit_success:        'Validare trimis\u0103 cu succes. V\u0103 mul\u021bumim!',
      submit_failed:         'Trimitere e\u0219uat\u0103 (HTTP {status}).\nDatele dvs. vor fi desc\u0103rcate ca fi\u0219ier JSON.\nV\u0103 rug\u0103m s\u0103 le trimite\u021bi prin e-mail coordonatorului de studiu.',
      submit_network_error:  'A ap\u0103rut o eroare de re\u021bea la trimitere.\nDatele dvs. vor fi desc\u0103rcate ca fi\u0219ier JSON.\nV\u0103 rug\u0103m s\u0103 le trimite\u021bi prin e-mail coordonatorului de studiu.',
      submitting:            'Se trimite\u2026',
      submit_btn:            'Trimite',
      submitted_check:       'Trimis \u2713',
      reviewed:              'Revizuit',
      pending:               '\u00cen a\u0219teptare',
      progress:              '{reviewed} din {total} revizuite',
      author_not_in_db:      '"{name}" ({id}) nu este \u00eenc\u0103 \u00een baza noastr\u0103 de date.\n\nPentru a fi inclus, v\u0103 rug\u0103m s\u0103 v\u0103 asigura\u021bi c\u0103 lucr\u0103rile dvs. sunt listate pe Shark References (https://www.shark-references.com) \u0219i contacta\u021bi echipa proiectului.'
    },
    el: {
      submit_no_reviews:     '\u03a0\u03b1\u03c1\u03b1\u03ba\u03b1\u03bb\u03ce \u03b5\u03bb\u03ad\u03b3\u03be\u03c4\u03b5 \u03c4\u03bf\u03c5\u03bb\u03ac\u03c7\u03b9\u03c3\u03c4\u03bf\u03bd \u03bc\u03af\u03b1 \u03b5\u03c1\u03b3\u03b1\u03c3\u03af\u03b1 \u03c0\u03c1\u03b9\u03bd \u03c4\u03b7\u03bd \u03c5\u03c0\u03bf\u03b2\u03bf\u03bb\u03ae.',
      submit_no_endpoint:    '\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03c1\u03c5\u03b8\u03bc\u03b9\u03c3\u03c4\u03b5\u03af \u03c3\u03b7\u03bc\u03b5\u03af\u03bf \u03c5\u03c0\u03bf\u03b2\u03bf\u03bb\u03ae\u03c2 \u03b3\u03b9\u03b1 \u03b1\u03c5\u03c4\u03ae\u03bd \u03c4\u03b7 \u03c3\u03b5\u03bb\u03af\u03b4\u03b1.\n\u03a4\u03b1 \u03b4\u03b5\u03b4\u03bf\u03bc\u03ad\u03bd\u03b1 \u03b5\u03c0\u03b9\u03ba\u03cd\u03c1\u03c9\u03c3\u03ae\u03c2 \u03c3\u03b1\u03c2 \u03b8\u03b1 \u03bb\u03b7\u03c6\u03b8\u03bf\u03cd\u03bd \u03c9\u03c2 \u03b1\u03c1\u03c7\u03b5\u03af\u03bf JSON.\n\u03a0\u03b1\u03c1\u03b1\u03ba\u03b1\u03bb\u03ce \u03c3\u03c4\u03b5\u03af\u03bb\u03c4\u03b5 \u03c4\u03bf \u03bc\u03ad\u03c3\u03c9 e-mail \u03c3\u03c4\u03bf\u03bd \u03c3\u03c5\u03bd\u03c4\u03bf\u03bd\u03b9\u03c3\u03c4\u03ae \u03c4\u03b7\u03c2 \u03bc\u03b5\u03bb\u03ad\u03c4\u03b7\u03c2.',
      submit_success:        '\u0397 \u03b5\u03c0\u03b9\u03ba\u03cd\u03c1\u03c9\u03c3\u03b7 \u03c5\u03c0\u03bf\u03b2\u03bb\u03ae\u03b8\u03b7\u03ba\u03b5 \u03bc\u03b5 \u03b5\u03c0\u03b9\u03c4\u03c5\u03c7\u03af\u03b1. \u0395\u03c5\u03c7\u03b1\u03c1\u03b9\u03c3\u03c4\u03bf\u03cd\u03bc\u03b5!',
      submit_failed:         '\u0397 \u03c5\u03c0\u03bf\u03b2\u03bf\u03bb\u03ae \u03b1\u03c0\u03ad\u03c4\u03c5\u03c7\u03b5 (HTTP {status}).\n\u03a4\u03b1 \u03b4\u03b5\u03b4\u03bf\u03bc\u03ad\u03bd\u03b1 \u03c3\u03b1\u03c2 \u03b8\u03b1 \u03bb\u03b7\u03c6\u03b8\u03bf\u03cd\u03bd \u03c9\u03c2 \u03b1\u03c1\u03c7\u03b5\u03af\u03bf JSON.\n\u03a0\u03b1\u03c1\u03b1\u03ba\u03b1\u03bb\u03ce \u03c3\u03c4\u03b5\u03af\u03bb\u03c4\u03b5 \u03c4\u03bf \u03bc\u03ad\u03c3\u03c9 e-mail \u03c3\u03c4\u03bf\u03bd \u03c3\u03c5\u03bd\u03c4\u03bf\u03bd\u03b9\u03c3\u03c4\u03ae \u03c4\u03b7\u03c2 \u03bc\u03b5\u03bb\u03ad\u03c4\u03b7\u03c2.',
      submit_network_error:  '\u03a0\u03b1\u03c1\u03bf\u03c5\u03c3\u03b9\u03ac\u03c3\u03c4\u03b7\u03ba\u03b5 \u03c3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03b4\u03b9\u03ba\u03c4\u03cd\u03bf\u03c5 \u03ba\u03b1\u03c4\u03ac \u03c4\u03b7\u03bd \u03c5\u03c0\u03bf\u03b2\u03bf\u03bb\u03ae.\n\u03a4\u03b1 \u03b4\u03b5\u03b4\u03bf\u03bc\u03ad\u03bd\u03b1 \u03c3\u03b1\u03c2 \u03b8\u03b1 \u03bb\u03b7\u03c6\u03b8\u03bf\u03cd\u03bd \u03c9\u03c2 \u03b1\u03c1\u03c7\u03b5\u03af\u03bf JSON.\n\u03a0\u03b1\u03c1\u03b1\u03ba\u03b1\u03bb\u03ce \u03c3\u03c4\u03b5\u03af\u03bb\u03c4\u03b5 \u03c4\u03bf \u03bc\u03ad\u03c3\u03c9 e-mail \u03c3\u03c4\u03bf\u03bd \u03c3\u03c5\u03bd\u03c4\u03bf\u03bd\u03b9\u03c3\u03c4\u03ae \u03c4\u03b7\u03c2 \u03bc\u03b5\u03bb\u03ad\u03c4\u03b7\u03c2.',
      submitting:            '\u03a5\u03c0\u03bf\u03b2\u03bf\u03bb\u03ae\u2026',
      submit_btn:            '\u03a5\u03c0\u03bf\u03b2\u03bf\u03bb\u03ae',
      submitted_check:       '\u03a5\u03c0\u03bf\u03b2\u03bb\u03ae\u03b8\u03b7\u03ba\u03b5 \u2713',
      reviewed:              '\u0395\u03bb\u03ad\u03b3\u03c7\u03b8\u03b7\u03ba\u03b5',
      pending:               '\u0395\u03ba\u03ba\u03c1\u03b5\u03bc\u03b5\u03af',
      progress:              '{reviewed} \u03b1\u03c0\u03cc {total} \u03b5\u03bb\u03b5\u03b3\u03bc\u03ad\u03bd\u03b1',
      author_not_in_db:      '\u03a4\u03bf "{name}" ({id}) \u03b4\u03b5\u03bd \u03b2\u03c1\u03af\u03c3\u03ba\u03b5\u03c4\u03b1\u03b9 \u03b1\u03ba\u03cc\u03bc\u03b7 \u03c3\u03c4\u03b7 \u03b2\u03ac\u03c3\u03b7 \u03b4\u03b5\u03b4\u03bf\u03bc\u03ad\u03bd\u03c9\u03bd \u03bc\u03b1\u03c2.\n\n\u0393\u03b9\u03b1 \u03bd\u03b1 \u03c3\u03c5\u03bc\u03c0\u03b5\u03c1\u03b9\u03bb\u03b7\u03c6\u03b8\u03b5\u03af\u03c4\u03b5, \u03b2\u03b5\u03b2\u03b1\u03b9\u03c9\u03b8\u03b5\u03af\u03c4\u03b5 \u03cc\u03c4\u03b9 \u03bf\u03b9 \u03b5\u03c1\u03b3\u03b1\u03c3\u03af\u03b5\u03c2 \u03c3\u03b1\u03c2 \u03b5\u03af\u03bd\u03b1\u03b9 \u03ba\u03b1\u03c4\u03b1\u03c7\u03c9\u03c1\u03b7\u03bc\u03ad\u03bd\u03b5\u03c2 \u03c3\u03c4\u03bf Shark References (https://www.shark-references.com) \u03ba\u03b1\u03b9 \u03b5\u03c0\u03b9\u03ba\u03bf\u03b9\u03bd\u03c9\u03bd\u03ae\u03c3\u03c4\u03b5 \u03bc\u03b5 \u03c4\u03b7\u03bd \u03bf\u03bc\u03ac\u03b4\u03b1 \u03c4\u03bf\u03c5 \u03ad\u03c1\u03b3\u03bf\u03c5.'
    },
    sv: {
      submit_no_reviews:     'V\u00e4nligen granska minst en artikel innan du skickar in.',
      submit_no_endpoint:    'Ingen inl\u00e4mnings\u00e4ndpunkt \u00e4r konfigurerad f\u00f6r denna sida.\nDina valideringsdata kommer att laddas ner som en JSON-fil.\nSkicka den via e-post till studiens koordinator.',
      submit_success:        'Valideringen har skickats in. Tack!',
      submit_failed:         'Inl\u00e4mningen misslyckades (HTTP {status}).\nDina data kommer att laddas ner som en JSON-fil.\nSkicka den via e-post till studiens koordinator.',
      submit_network_error:  'Ett n\u00e4tverksfel uppstod vid inl\u00e4mningen.\nDina data kommer att laddas ner som en JSON-fil.\nSkicka den via e-post till studiens koordinator.',
      submitting:            'Skickar\u2026',
      submit_btn:            'Skicka in',
      submitted_check:       'Skickat \u2713',
      reviewed:              'Granskad',
      pending:               'V\u00e4ntande',
      progress:              '{reviewed} av {total} granskade',
      author_not_in_db:      '"{name}" ({id}) finns inte \u00e4nnu i v\u00e5r databas.\n\nF\u00f6r att inkluderas, se till att dina artiklar finns listade p\u00e5 Shark References (https://www.shark-references.com) och kontakta projektteamet.'
    },
    da: {
      submit_no_reviews:     'Gennemg\u00e5 venligst mindst \u00e9n artikel f\u00f8r indsendelse.',
      submit_no_endpoint:    'Der er ikke konfigureret et indsendelsesslutpunkt for denne side.\nDine valideringsdata downloades som en JSON-fil.\nSend den venligst via e-mail til studiekoordinatoren.',
      submit_success:        'Validering indsendt. Tak!',
      submit_failed:         'Indsendelse mislykkedes (HTTP {status}).\nDine data downloades som en JSON-fil.\nSend den venligst via e-mail til studiekoordinatoren.',
      submit_network_error:  'Der opstod en netv\u00e6rksfejl under indsendelsen.\nDine data downloades som en JSON-fil.\nSend den venligst via e-mail til studiekoordinatoren.',
      submitting:            'Sender\u2026',
      submit_btn:            'Indsend',
      submitted_check:       'Indsendt \u2713',
      reviewed:              'Gennemg\u00e5et',
      pending:               'Afventer',
      progress:              '{reviewed} af {total} gennemg\u00e5et',
      author_not_in_db:      '"{name}" ({id}) er ikke endnu i vores database.\n\nFor at blive inkluderet, s\u00f8rg venligst for, at dine artikler er anf\u00f8rt p\u00e5 Shark References (https://www.shark-references.com), og kontakt projektteamet.'
    },
    no: {
      submit_no_reviews:     'Vennligst gjennomg\u00e5 minst \u00e9n artikkel f\u00f8r innsending.',
      submit_no_endpoint:    'Ingen innsendings-endepunkt er konfigurert for denne siden.\nValideringsdataene dine lastes ned som en JSON-fil.\nVennligst send den via e-post til studiekoordinatoren.',
      submit_success:        'Validering sendt inn. Takk!',
      submit_failed:         'Innsending mislyktes (HTTP {status}).\nDataene dine lastes ned som en JSON-fil.\nVennligst send den via e-post til studiekoordinatoren.',
      submit_network_error:  'Det oppstod en nettverksfeil under innsendingen.\nDataene dine lastes ned som en JSON-fil.\nVennligst send den via e-post til studiekoordinatoren.',
      submitting:            'Sender\u2026',
      submit_btn:            'Send inn',
      submitted_check:       'Sendt \u2713',
      reviewed:              'Gjennomg\u00e5tt',
      pending:               'Avventer',
      progress:              '{reviewed} av {total} gjennomg\u00e5tt',
      author_not_in_db:      '"{name}" ({id}) er ikke enn\u00e5 i databasen v\u00e5r.\n\nFor \u00e5 bli inkludert, s\u00f8rg for at artiklene dine er oppf\u00f8rt p\u00e5 Shark References (https://www.shark-references.com) og kontakt prosjektteamet.'
    },
    fi: {
      submit_no_reviews:     'Tarkista v\u00e4hint\u00e4\u00e4n yksi artikkeli ennen l\u00e4hett\u00e4mist\u00e4.',
      submit_no_endpoint:    'T\u00e4lle sivulle ei ole m\u00e4\u00e4ritetty l\u00e4hetysp\u00e4\u00e4tepistett\u00e4.\nValidointitiedostosi ladataan JSON-tiedostona.\nL\u00e4het\u00e4 se s\u00e4hk\u00f6postitse tutkimuksen koordinaattorille.',
      submit_success:        'Validointi l\u00e4hetetty. Kiitos!',
      submit_failed:         'L\u00e4hetys ep\u00e4onnistui (HTTP {status}).\nTiedostosi ladataan JSON-tiedostona.\nL\u00e4het\u00e4 se s\u00e4hk\u00f6postitse tutkimuksen koordinaattorille.',
      submit_network_error:  'L\u00e4hetyksen aikana tapahtui verkkovirhe.\nTiedostosi ladataan JSON-tiedostona.\nL\u00e4het\u00e4 se s\u00e4hk\u00f6postitse tutkimuksen koordinaattorille.',
      submitting:            'L\u00e4hetet\u00e4\u00e4n\u2026',
      submit_btn:            'L\u00e4het\u00e4',
      submitted_check:       'L\u00e4hetetty \u2713',
      reviewed:              'Tarkistettu',
      pending:               'Odottaa',
      progress:              '{reviewed} / {total} tarkistettu',
      author_not_in_db:      '"{name}" ({id}) ei ole viel\u00e4 tietokannassamme.\n\nJotta sinut voidaan sis\u00e4llytt\u00e4\u00e4, varmista, ett\u00e4 artikkelisi on lueteltu Shark References -sivustolla (https://www.shark-references.com), ja ota yhteytt\u00e4 projektitiimiin.'
    },
    ru: {
      submit_no_reviews:     '\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0445\u043e\u0442\u044f \u0431\u044b \u043e\u0434\u043d\u0443 \u0441\u0442\u0430\u0442\u044c\u044e \u043f\u0435\u0440\u0435\u0434 \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u043e\u0439.',
      submit_no_endpoint:    '\u0414\u043b\u044f \u044d\u0442\u043e\u0439 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b \u043d\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u0430 \u043a\u043e\u043d\u0435\u0447\u043d\u0430\u044f \u0442\u043e\u0447\u043a\u0430 \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u0438.\n\u0412\u0430\u0448\u0438 \u0434\u0430\u043d\u043d\u044b\u0435 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u0431\u0443\u0434\u0443\u0442 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u044b \u0432 \u0432\u0438\u0434\u0435 \u0444\u0430\u0439\u043b\u0430 JSON.\n\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u043e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0435\u0433\u043e \u043f\u043e \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u043e\u0439 \u043f\u043e\u0447\u0442\u0435 \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u043e\u0440\u0443 \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u044f.',
      submit_success:        '\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0430. \u0421\u043f\u0430\u0441\u0438\u0431\u043e!',
      submit_failed:         '\u0421\u0431\u043e\u0439 \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u0438 (HTTP {status}).\n\u0412\u0430\u0448\u0438 \u0434\u0430\u043d\u043d\u044b\u0435 \u0431\u0443\u0434\u0443\u0442 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u044b \u0432 \u0432\u0438\u0434\u0435 \u0444\u0430\u0439\u043b\u0430 JSON.\n\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u043e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0435\u0433\u043e \u043f\u043e \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u043e\u0439 \u043f\u043e\u0447\u0442\u0435 \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u043e\u0440\u0443 \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u044f.',
      submit_network_error:  '\u041f\u0440\u043e\u0438\u0437\u043e\u0448\u043b\u0430 \u0441\u0435\u0442\u0435\u0432\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u0435.\n\u0412\u0430\u0448\u0438 \u0434\u0430\u043d\u043d\u044b\u0435 \u0431\u0443\u0434\u0443\u0442 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u044b \u0432 \u0432\u0438\u0434\u0435 \u0444\u0430\u0439\u043b\u0430 JSON.\n\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u043e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0435\u0433\u043e \u043f\u043e \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u043e\u0439 \u043f\u043e\u0447\u0442\u0435 \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u043e\u0440\u0443 \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u044f.',
      submitting:            '\u041e\u0442\u043f\u0440\u0430\u0432\u043a\u0430\u2026',
      submit_btn:            '\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c',
      submitted_check:       '\u041e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e \u2713',
      reviewed:              '\u041f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043e',
      pending:               '\u041e\u0436\u0438\u0434\u0430\u0435\u0442',
      progress:              '{reviewed} \u0438\u0437 {total} \u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043e',
      author_not_in_db:      '"{name}" ({id}) \u043f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0432 \u043d\u0430\u0448\u0435\u0439 \u0431\u0430\u0437\u0435 \u0434\u0430\u043d\u043d\u044b\u0445.\n\n\u0427\u0442\u043e\u0431\u044b \u0431\u044b\u0442\u044c \u0432\u043a\u043b\u044e\u0447\u0435\u043d\u043d\u044b\u043c, \u0443\u0431\u0435\u0434\u0438\u0442\u0435\u0441\u044c, \u0447\u0442\u043e \u0432\u0430\u0448\u0438 \u0441\u0442\u0430\u0442\u044c\u0438 \u0443\u043a\u0430\u0437\u0430\u043d\u044b \u043d\u0430 Shark References (https://www.shark-references.com), \u0438 \u0441\u0432\u044f\u0436\u0438\u0442\u0435\u0441\u044c \u0441 \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 \u043f\u0440\u043e\u0435\u043a\u0442\u0430.'
    },
    uk: {
      submit_no_reviews:     '\u0411\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430, \u043f\u0435\u0440\u0435\u0433\u043b\u044f\u043d\u044c\u0442\u0435 \u0449\u043e\u043d\u0430\u0439\u043c\u0435\u043d\u0448\u0435 \u043e\u0434\u043d\u0443 \u0441\u0442\u0430\u0442\u0442\u044e \u043f\u0435\u0440\u0435\u0434 \u043d\u0430\u0434\u0441\u0438\u043b\u0430\u043d\u043d\u044f\u043c.',
      submit_no_endpoint:    '\u0414\u043b\u044f \u0446\u0456\u0454\u0457 \u0441\u0442\u043e\u0440\u0456\u043d\u043a\u0438 \u043d\u0435 \u043d\u0430\u043b\u0430\u0448\u0442\u043e\u0432\u0430\u043d\u043e \u043a\u0456\u043d\u0446\u0435\u0432\u0443 \u0442\u043e\u0447\u043a\u0443 \u043d\u0430\u0434\u0441\u0438\u043b\u0430\u043d\u043d\u044f.\n\u0412\u0430\u0448\u0456 \u0434\u0430\u043d\u0456 \u0432\u0430\u043b\u0456\u0434\u0430\u0446\u0456\u0457 \u0431\u0443\u0434\u0435 \u0437\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043e \u044f\u043a \u0444\u0430\u0439\u043b JSON.\n\u0411\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430, \u043d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u0439\u043e\u0433\u043e \u0435\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u043e\u044e \u043f\u043e\u0448\u0442\u043e\u044e \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u043e\u0440\u0443 \u0434\u043e\u0441\u043b\u0456\u0434\u0436\u0435\u043d\u043d\u044f.',
      submit_success:        '\u0412\u0430\u043b\u0456\u0434\u0430\u0446\u0456\u044e \u0443\u0441\u043f\u0456\u0448\u043d\u043e \u043d\u0430\u0434\u0456\u0441\u043b\u0430\u043d\u043e. \u0414\u044f\u043a\u0443\u0454\u043c\u043e!',
      submit_failed:         '\u041d\u0430\u0434\u0441\u0438\u043b\u0430\u043d\u043d\u044f \u043d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044f (HTTP {status}).\n\u0412\u0430\u0448\u0456 \u0434\u0430\u043d\u0456 \u0431\u0443\u0434\u0435 \u0437\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043e \u044f\u043a \u0444\u0430\u0439\u043b JSON.\n\u0411\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430, \u043d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u0439\u043e\u0433\u043e \u0435\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u043e\u044e \u043f\u043e\u0448\u0442\u043e\u044e \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u043e\u0440\u0443 \u0434\u043e\u0441\u043b\u0456\u0434\u0436\u0435\u043d\u043d\u044f.',
      submit_network_error:  '\u041f\u0456\u0434 \u0447\u0430\u0441 \u043d\u0430\u0434\u0441\u0438\u043b\u0430\u043d\u043d\u044f \u0441\u0442\u0430\u043b\u0430\u0441\u044f \u043c\u0435\u0440\u0435\u0436\u0435\u0432\u0430 \u043f\u043e\u043c\u0438\u043b\u043a\u0430.\n\u0412\u0430\u0448\u0456 \u0434\u0430\u043d\u0456 \u0431\u0443\u0434\u0435 \u0437\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043e \u044f\u043a \u0444\u0430\u0439\u043b JSON.\n\u0411\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430, \u043d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u0439\u043e\u0433\u043e \u0435\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u043e\u044e \u043f\u043e\u0448\u0442\u043e\u044e \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u043e\u0440\u0443 \u0434\u043e\u0441\u043b\u0456\u0434\u0436\u0435\u043d\u043d\u044f.',
      submitting:            '\u041d\u0430\u0434\u0441\u0438\u043b\u0430\u043d\u043d\u044f\u2026',
      submit_btn:            '\u041d\u0430\u0434\u0456\u0441\u043b\u0430\u0442\u0438',
      submitted_check:       '\u041d\u0430\u0434\u0456\u0441\u043b\u0430\u043d\u043e \u2713',
      reviewed:              '\u041f\u0435\u0440\u0435\u0432\u0456\u0440\u0435\u043d\u043e',
      pending:               '\u041e\u0447\u0456\u043a\u0443\u0454',
      progress:              '{reviewed} \u0437 {total} \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u0435\u043d\u043e',
      author_not_in_db:      '"{name}" ({id}) \u0449\u0435 \u043d\u0435\u043c\u0430\u0454 \u0432 \u043d\u0430\u0448\u0456\u0439 \u0431\u0430\u0437\u0456 \u0434\u0430\u043d\u0438\u0445.\n\n\u0429\u043e\u0431 \u0431\u0443\u0442\u0438 \u0432\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u043c, \u043f\u0435\u0440\u0435\u043a\u043e\u043d\u0430\u0439\u0442\u0435\u0441\u044f, \u0449\u043e \u0432\u0430\u0448\u0456 \u0441\u0442\u0430\u0442\u0442\u0456 \u0432\u043a\u0430\u0437\u0430\u043d\u043e \u043d\u0430 Shark References (https://www.shark-references.com), \u0456 \u0437\u0432\'\u044f\u0436\u0456\u0442\u044c\u0441\u044f \u0437 \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u044e \u043f\u0440\u043e\u0454\u043a\u0442\u0443.'
    },
    tr: {
      submit_no_reviews:     'L\u00fctfen g\u00f6ndermeden \u00f6nce en az bir makaleyi inceleyin.',
      submit_no_endpoint:    'Bu sayfa i\u00e7in bir g\u00f6nderim u\u00e7 noktas\u0131 yap\u0131land\u0131r\u0131lmam\u0131\u015f.\nDo\u011frulama verileriniz bir JSON dosyas\u0131 olarak indirilecektir.\nL\u00fctfen \u00e7al\u0131\u015fma koordinat\u00f6r\u00fcne e-posta ile g\u00f6nderin.',
      submit_success:        'Do\u011frulama ba\u015far\u0131yla g\u00f6nderildi. Te\u015fekk\u00fcrler!',
      submit_failed:         'G\u00f6nderim ba\u015far\u0131s\u0131z (HTTP {status}).\nVerileriniz bir JSON dosyas\u0131 olarak indirilecektir.\nL\u00fctfen \u00e7al\u0131\u015fma koordinat\u00f6r\u00fcne e-posta ile g\u00f6nderin.',
      submit_network_error:  'G\u00f6nderim s\u0131ras\u0131nda bir a\u011f hatas\u0131 olu\u015ftu.\nVerileriniz bir JSON dosyas\u0131 olarak indirilecektir.\nL\u00fctfen \u00e7al\u0131\u015fma koordinat\u00f6r\u00fcne e-posta ile g\u00f6nderin.',
      submitting:            'G\u00f6nderiliyor\u2026',
      submit_btn:            'G\u00f6nder',
      submitted_check:       'G\u00f6nderildi \u2713',
      reviewed:              '\u0130ncelendi',
      pending:               'Beklemede',
      progress:              '{reviewed} / {total} incelendi',
      author_not_in_db:      '"{name}" ({id}) hen\u00fcz veritaban\u0131m\u0131zda de\u011fil.\n\nDahil edilmek i\u00e7in, makalelerinizin Shark References\'te (https://www.shark-references.com) listelendi\u011finden emin olun ve proje ekibiyle ileti\u015fime ge\u00e7in.'
    },
    ar: {
      submit_no_reviews:     '\u064a\u0631\u062c\u0649 \u0645\u0631\u0627\u062c\u0639\u0629 \u0648\u0631\u0642\u0629 \u0648\u0627\u062d\u062f\u0629 \u0639\u0644\u0649 \u0627\u0644\u0623\u0642\u0644 \u0642\u0628\u0644 \u0627\u0644\u0625\u0631\u0633\u0627\u0644.',
      submit_no_endpoint:    '\u0644\u0645 \u064a\u062a\u0645 \u062a\u0643\u0648\u064a\u0646 \u0646\u0642\u0637\u0629 \u0625\u0631\u0633\u0627\u0644 \u0644\u0647\u0630\u0647 \u0627\u0644\u0635\u0641\u062d\u0629.\n\u0633\u064a\u062a\u0645 \u062a\u0646\u0632\u064a\u0644 \u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u062a\u062d\u0642\u0642 \u0627\u0644\u062e\u0627\u0635\u0629 \u0628\u0643 \u0643\u0645\u0644\u0641 JSON.\n\u064a\u0631\u062c\u0649 \u0625\u0631\u0633\u0627\u0644\u0647\u0627 \u0628\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0625\u0644\u0649 \u0645\u0646\u0633\u0642 \u0627\u0644\u062f\u0631\u0627\u0633\u0629.',
      submit_success:        '\u062a\u0645 \u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u062a\u062d\u0642\u0642 \u0628\u0646\u062c\u0627\u062d. \u0634\u0643\u0631\u064b\u0627 \u0644\u0643!',
      submit_failed:         '\u0641\u0634\u0644 \u0627\u0644\u0625\u0631\u0633\u0627\u0644 (HTTP {status}).\n\u0633\u064a\u062a\u0645 \u062a\u0646\u0632\u064a\u0644 \u0628\u064a\u0627\u0646\u0627\u062a\u0643 \u0643\u0645\u0644\u0641 JSON.\n\u064a\u0631\u062c\u0649 \u0625\u0631\u0633\u0627\u0644\u0647\u0627 \u0628\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0625\u0644\u0649 \u0645\u0646\u0633\u0642 \u0627\u0644\u062f\u0631\u0627\u0633\u0629.',
      submit_network_error:  '\u062d\u062f\u062b \u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0634\u0628\u0643\u0629 \u0623\u062b\u0646\u0627\u0621 \u0627\u0644\u0625\u0631\u0633\u0627\u0644.\n\u0633\u064a\u062a\u0645 \u062a\u0646\u0632\u064a\u0644 \u0628\u064a\u0627\u0646\u0627\u062a\u0643 \u0643\u0645\u0644\u0641 JSON.\n\u064a\u0631\u062c\u0649 \u0625\u0631\u0633\u0627\u0644\u0647\u0627 \u0628\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0625\u0644\u0649 \u0645\u0646\u0633\u0642 \u0627\u0644\u062f\u0631\u0627\u0633\u0629.',
      submitting:            '\u062c\u0627\u0631\u064d \u0627\u0644\u0625\u0631\u0633\u0627\u0644\u2026',
      submit_btn:            '\u0625\u0631\u0633\u0627\u0644',
      submitted_check:       '\u062a\u0645 \u0627\u0644\u0625\u0631\u0633\u0627\u0644 \u2713',
      reviewed:              '\u062a\u0645\u062a \u0627\u0644\u0645\u0631\u0627\u062c\u0639\u0629',
      pending:               '\u0642\u064a\u062f \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631',
      progress:              '{reviewed} \u0645\u0646 {total} \u062a\u0645\u062a \u0645\u0631\u0627\u062c\u0639\u062a\u0647\u0627',
      author_not_in_db:      '"{name}" ({id}) \u063a\u064a\u0631 \u0645\u062f\u0631\u062c \u0628\u0639\u062f \u0641\u064a \u0642\u0627\u0639\u062f\u0629 \u0628\u064a\u0627\u0646\u0627\u062a\u0646\u0627.\n\n\u0644\u0643\u064a \u064a\u062a\u0645 \u062a\u0636\u0645\u064a\u0646\u0643\u060c \u064a\u0631\u062c\u0649 \u0627\u0644\u062a\u0623\u0643\u062f \u0645\u0646 \u0623\u0646 \u0623\u0648\u0631\u0627\u0642\u0643 \u0645\u062f\u0631\u062c\u0629 \u0641\u064a Shark References (https://www.shark-references.com) \u0648\u0627\u0644\u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0641\u0631\u064a\u0642 \u0627\u0644\u0645\u0634\u0631\u0648\u0639.'
    },
    he: {
      submit_no_reviews:     '\u05d0\u05e0\u05d0 \u05d1\u05d3\u05d5\u05e7 \u05dc\u05e4\u05d7\u05d5\u05ea \u05de\u05d0\u05de\u05e8 \u05d0\u05d7\u05d3 \u05dc\u05e4\u05e0\u05d9 \u05d4\u05e9\u05dc\u05d9\u05d7\u05d4.',
      submit_no_endpoint:    '\u05dc\u05d0 \u05d4\u05d5\u05d2\u05d3\u05e8\u05d4 \u05e0\u05e7\u05d5\u05d3\u05ea \u05e7\u05e6\u05d4 \u05dc\u05e9\u05dc\u05d9\u05d7\u05d4 \u05e2\u05d1\u05d5\u05e8 \u05d3\u05e3 \u05d6\u05d4.\n\u05e0\u05ea\u05d5\u05e0\u05d9 \u05d4\u05d0\u05d9\u05de\u05d5\u05ea \u05e9\u05dc\u05da \u05d9\u05d5\u05e8\u05d3\u05d5 \u05db\u05e7\u05d5\u05d1\u05e5 JSON.\n\u05d0\u05e0\u05d0 \u05e9\u05dc\u05d7 \u05d0\u05d5\u05ea\u05dd \u05d1\u05d3\u05d5\u05d0\u05f4\u05dc \u05dc\u05de\u05ea\u05d0\u05dd \u05d4\u05de\u05d7\u05e7\u05e8.',
      submit_success:        '\u05d4\u05d0\u05d9\u05de\u05d5\u05ea \u05e0\u05e9\u05dc\u05d7\u05d4 \u05d1\u05d4\u05e6\u05dc\u05d7\u05d4. \u05ea\u05d5\u05d3\u05d4!',
      submit_failed:         '\u05d4\u05e9\u05dc\u05d9\u05d7\u05d4 \u05e0\u05db\u05e9\u05dc\u05d4 (HTTP {status}).\n\u05d4\u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05e9\u05dc\u05da \u05d9\u05d5\u05e8\u05d3\u05d5 \u05db\u05e7\u05d5\u05d1\u05e5 JSON.\n\u05d0\u05e0\u05d0 \u05e9\u05dc\u05d7 \u05d0\u05d5\u05ea\u05dd \u05d1\u05d3\u05d5\u05d0\u05f4\u05dc \u05dc\u05de\u05ea\u05d0\u05dd \u05d4\u05de\u05d7\u05e7\u05e8.',
      submit_network_error:  '\u05d0\u05d9\u05e8\u05e2\u05d4 \u05e9\u05d2\u05d9\u05d0\u05ea \u05e8\u05e9\u05ea \u05d1\u05de\u05d4\u05dc\u05da \u05d4\u05e9\u05dc\u05d9\u05d7\u05d4.\n\u05d4\u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05e9\u05dc\u05da \u05d9\u05d5\u05e8\u05d3\u05d5 \u05db\u05e7\u05d5\u05d1\u05e5 JSON.\n\u05d0\u05e0\u05d0 \u05e9\u05dc\u05d7 \u05d0\u05d5\u05ea\u05dd \u05d1\u05d3\u05d5\u05d0\u05f4\u05dc \u05dc\u05de\u05ea\u05d0\u05dd \u05d4\u05de\u05d7\u05e7\u05e8.',
      submitting:            '\u05e9\u05d5\u05dc\u05d7\u2026',
      submit_btn:            '\u05e9\u05dc\u05d7',
      submitted_check:       '\u05e0\u05e9\u05dc\u05d7 \u2713',
      reviewed:              '\u05e0\u05d1\u05d3\u05e7',
      pending:               '\u05d1\u05d4\u05de\u05ea\u05e0\u05d4',
      progress:              '{reviewed} \u05de\u05ea\u05d5\u05da {total} \u05e0\u05d1\u05d3\u05e7\u05d5',
      author_not_in_db:      '"{name}" ({id}) \u05d0\u05d9\u05e0\u05d5 \u05e0\u05de\u05e6\u05d0 \u05e2\u05d3\u05d9\u05d9\u05df \u05d1\u05de\u05e1\u05d3 \u05d4\u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05e9\u05dc\u05e0\u05d5.\n\n\u05db\u05d3\u05d9 \u05dc\u05d4\u05d9\u05db\u05dc\u05dc, \u05d5\u05d3\u05d0 \u05e9\u05d4\u05de\u05d0\u05de\u05e8\u05d9\u05dd \u05e9\u05dc\u05da \u05e8\u05e9\u05d5\u05de\u05d9\u05dd \u05d1-Shark References (https://www.shark-references.com) \u05d5\u05e6\u05d5\u05e8 \u05e7\u05e9\u05e8 \u05e2\u05dd \u05e6\u05d5\u05d5\u05ea \u05d4\u05e4\u05e8\u05d5\u05d9\u05e7\u05d8.'
    },
    zh: {
      submit_no_reviews:     '\u8bf7\u5728\u63d0\u4ea4\u524d\u81f3\u5c11\u5ba1\u9605\u4e00\u7bc7\u8bba\u6587\u3002',
      submit_no_endpoint:    '\u6b64\u9875\u9762\u672a\u914d\u7f6e\u63d0\u4ea4\u7aef\u70b9\u3002\n\u60a8\u7684\u9a8c\u8bc1\u6570\u636e\u5c06\u4e0b\u8f7d\u4e3a JSON \u6587\u4ef6\u3002\n\u8bf7\u901a\u8fc7\u7535\u5b50\u90ae\u4ef6\u53d1\u9001\u7ed9\u7814\u7a76\u534f\u8c03\u5458\u3002',
      submit_success:        '\u9a8c\u8bc1\u63d0\u4ea4\u6210\u529f\u3002\u8c22\u8c22\uff01',
      submit_failed:         '\u63d0\u4ea4\u5931\u8d25 (HTTP {status})\u3002\n\u60a8\u7684\u6570\u636e\u5c06\u4e0b\u8f7d\u4e3a JSON \u6587\u4ef6\u3002\n\u8bf7\u901a\u8fc7\u7535\u5b50\u90ae\u4ef6\u53d1\u9001\u7ed9\u7814\u7a76\u534f\u8c03\u5458\u3002',
      submit_network_error:  '\u63d0\u4ea4\u671f\u95f4\u53d1\u751f\u7f51\u7edc\u9519\u8bef\u3002\n\u60a8\u7684\u6570\u636e\u5c06\u4e0b\u8f7d\u4e3a JSON \u6587\u4ef6\u3002\n\u8bf7\u901a\u8fc7\u7535\u5b50\u90ae\u4ef6\u53d1\u9001\u7ed9\u7814\u7a76\u534f\u8c03\u5458\u3002',
      submitting:            '\u6b63\u5728\u63d0\u4ea4\u2026',
      submit_btn:            '\u63d0\u4ea4',
      submitted_check:       '\u5df2\u63d0\u4ea4 \u2713',
      reviewed:              '\u5df2\u5ba1\u9605',
      pending:               '\u5f85\u5ba1\u9605',
      progress:              '\u5df2\u5ba1\u9605 {reviewed} / {total}',
      author_not_in_db:      '"{name}" ({id}) \u5c1a\u672a\u5728\u6211\u4eec\u7684\u6570\u636e\u5e93\u4e2d\u3002\n\n\u8981\u88ab\u6536\u5f55\uff0c\u8bf7\u786e\u4fdd\u60a8\u7684\u8bba\u6587\u5df2\u5217\u5728 Shark References (https://www.shark-references.com) \u4e0a\uff0c\u5e76\u8054\u7cfb\u9879\u76ee\u56e2\u961f\u3002'
    },
    ja: {
      submit_no_reviews:     '\u9001\u4fe1\u524d\u306b\u5c11\u306a\u304f\u3068\u3082 1 \u4ef6\u306e\u8ad6\u6587\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002',
      submit_no_endpoint:    '\u3053\u306e\u30da\u30fc\u30b8\u306b\u306f\u9001\u4fe1\u30a8\u30f3\u30c9\u30dd\u30a4\u30f3\u30c8\u304c\u69cb\u6210\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002\n\u691c\u8a3c\u30c7\u30fc\u30bf\u306f JSON \u30d5\u30a1\u30a4\u30eb\u3068\u3057\u3066\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9\u3055\u308c\u307e\u3059\u3002\n\u7814\u7a76\u30b3\u30fc\u30c7\u30a3\u30cd\u30fc\u30bf\u30fc\u306b\u30e1\u30fc\u30eb\u3067\u9001\u4fe1\u3057\u3066\u304f\u3060\u3055\u3044\u3002',
      submit_success:        '\u691c\u8a3c\u3092\u6b63\u5e38\u306b\u9001\u4fe1\u3057\u307e\u3057\u305f\u3002\u3042\u308a\u304c\u3068\u3046\u3054\u3056\u3044\u307e\u3057\u305f\uff01',
      submit_failed:         '\u9001\u4fe1\u306b\u5931\u6557\u3057\u307e\u3057\u305f (HTTP {status})\u3002\n\u30c7\u30fc\u30bf\u306f JSON \u30d5\u30a1\u30a4\u30eb\u3068\u3057\u3066\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9\u3055\u308c\u307e\u3059\u3002\n\u7814\u7a76\u30b3\u30fc\u30c7\u30a3\u30cd\u30fc\u30bf\u30fc\u306b\u30e1\u30fc\u30eb\u3067\u9001\u4fe1\u3057\u3066\u304f\u3060\u3055\u3044\u3002',
      submit_network_error:  '\u9001\u4fe1\u4e2d\u306b\u30cd\u30c3\u30c8\u30ef\u30fc\u30af\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002\n\u30c7\u30fc\u30bf\u306f JSON \u30d5\u30a1\u30a4\u30eb\u3068\u3057\u3066\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9\u3055\u308c\u307e\u3059\u3002\n\u7814\u7a76\u30b3\u30fc\u30c7\u30a3\u30cd\u30fc\u30bf\u30fc\u306b\u30e1\u30fc\u30eb\u3067\u9001\u4fe1\u3057\u3066\u304f\u3060\u3055\u3044\u3002',
      submitting:            '\u9001\u4fe1\u4e2d\u2026',
      submit_btn:            '\u9001\u4fe1',
      submitted_check:       '\u9001\u4fe1\u6e08\u307f \u2713',
      reviewed:              '\u78ba\u8a8d\u6e08\u307f',
      pending:               '\u672a\u51e6\u7406',
      progress:              '{total} \u4ef6\u4e2d {reviewed} \u4ef6\u78ba\u8a8d\u6e08\u307f',
      author_not_in_db:      '\u300c{name}\u300d({id}) \u306f\u307e\u3060\u30c7\u30fc\u30bf\u30d9\u30fc\u30b9\u306b\u767b\u9332\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002\n\n\u8ffd\u52a0\u3059\u308b\u306b\u306f\u3001\u8ad6\u6587\u304c Shark References (https://www.shark-references.com) \u306b\u63b2\u8f09\u3055\u308c\u3066\u3044\u308b\u3053\u3068\u3092\u78ba\u8a8d\u3057\u3001\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30c1\u30fc\u30e0\u306b\u304a\u554f\u3044\u5408\u308f\u305b\u304f\u3060\u3055\u3044\u3002'
    },
    ko: {
      submit_no_reviews:     '\uc81c\ucd9c\ud558\uae30 \uc804\uc5d0 \ucd5c\uc18c \ud55c \ud3b8\uc758 \ub17c\ubb38\uc744 \uac80\ud1a0\ud558\uc138\uc694.',
      submit_no_endpoint:    '\uc774 \ud398\uc774\uc9c0\uc5d0 \ub300\ud55c \uc81c\ucd9c \uc5d4\ub4dc\ud3ec\uc778\ud2b8\uac00 \uad6c\uc131\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.\n\uac80\uc99d \ub370\uc774\ud130\uac00 JSON \ud30c\uc77c\ub85c \ub2e4\uc6b4\ub85c\ub4dc\ub429\ub2c8\ub2e4.\n\uc5f0\uad6c \ucc45\uc784\uc790\uc5d0\uac8c \uc774\uba54\uc77c\ub85c \ubcf4\ub0b4\uc8fc\uc138\uc694.',
      submit_success:        '\uac80\uc99d\uc774 \uc131\uacf5\uc801\uc73c\ub85c \uc81c\ucd9c\ub418\uc5c8\uc2b5\ub2c8\ub2e4. \uac10\uc0ac\ud569\ub2c8\ub2e4!',
      submit_failed:         '\uc81c\ucd9c \uc2e4\ud328 (HTTP {status}).\n\ub370\uc774\ud130\uac00 JSON \ud30c\uc77c\ub85c \ub2e4\uc6b4\ub85c\ub4dc\ub429\ub2c8\ub2e4.\n\uc5f0\uad6c \ucc45\uc784\uc790\uc5d0\uac8c \uc774\uba54\uc77c\ub85c \ubcf4\ub0b4\uc8fc\uc138\uc694.',
      submit_network_error:  '\uc81c\ucd9c \uc911 \ub124\ud2b8\uc6cc\ud06c \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.\n\ub370\uc774\ud130\uac00 JSON \ud30c\uc77c\ub85c \ub2e4\uc6b4\ub85c\ub4dc\ub429\ub2c8\ub2e4.\n\uc5f0\uad6c \ucc45\uc784\uc790\uc5d0\uac8c \uc774\uba54\uc77c\ub85c \ubcf4\ub0b4\uc8fc\uc138\uc694.',
      submitting:            '\uc81c\ucd9c \uc911\u2026',
      submit_btn:            '\uc81c\ucd9c',
      submitted_check:       '\uc81c\ucd9c\ub428 \u2713',
      reviewed:              '\uac80\ud1a0\ub428',
      pending:               '\ub300\uae30 \uc911',
      progress:              '{total}\uac1c \uc911 {reviewed}\uac1c \uac80\ud1a0\ub428',
      author_not_in_db:      '"{name}" ({id})\uc740(\ub294) \uc544\uc9c1 \ub370\uc774\ud130\ubca0\uc774\uc2a4\uc5d0 \uc5c6\uc2b5\ub2c8\ub2e4.\n\n\ud3ec\ud568\ub418\ub824\uba74 \ub17c\ubb38\uc774 Shark References (https://www.shark-references.com)\uc5d0 \ub4f1\ub85d\ub418\uc5b4 \uc788\ub294\uc9c0 \ud655\uc778\ud558\uace0 \ud504\ub85c\uc81d\ud2b8 \ud300\uc5d0 \ubb38\uc758\ud558\uc138\uc694.'
    },
    id: {
      submit_no_reviews:     'Harap tinjau setidaknya satu makalah sebelum mengirim.',
      submit_no_endpoint:    'Tidak ada titik akhir pengiriman yang dikonfigurasi untuk halaman ini.\nData validasi Anda akan diunduh sebagai file JSON.\nKirim melalui e-mail kepada koordinator studi.',
      submit_success:        'Validasi berhasil dikirim. Terima kasih!',
      submit_failed:         'Pengiriman gagal (HTTP {status}).\nData Anda akan diunduh sebagai file JSON.\nKirim melalui e-mail kepada koordinator studi.',
      submit_network_error:  'Terjadi kesalahan jaringan selama pengiriman.\nData Anda akan diunduh sebagai file JSON.\nKirim melalui e-mail kepada koordinator studi.',
      submitting:            'Mengirim\u2026',
      submit_btn:            'Kirim',
      submitted_check:       'Terkirim \u2713',
      reviewed:              'Ditinjau',
      pending:               'Tertunda',
      progress:              '{reviewed} dari {total} ditinjau',
      author_not_in_db:      '"{name}" ({id}) belum ada dalam basis data kami.\n\nUntuk disertakan, pastikan makalah Anda terdaftar di Shark References (https://www.shark-references.com) dan hubungi tim proyek.'
    }
  };

  function _t(key, vars) {
    var bag = _I18N_STRINGS[_lang] || _I18N_STRINGS.en;
    var str = (bag && bag[key] != null) ? bag[key]
                : (_I18N_STRINGS.en[key] != null ? _I18N_STRINGS.en[key] : key);
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        str = str.replace(new RegExp('\\{' + k + '\\}', 'g'), String(vars[k]));
      });
    }
    return str;
  }

  window.I18N = { t: _t, lang: _lang, languages: Object.keys(_I18N_STRINGS) };

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  var TIER1_PREFIXES = ['b_', 'sb_', 'd_', 'eco_', 'pr_', 'imp_', 'gear_', 'ob_'];
  var TIER1_CHECKBOX = ['b_', 'sb_', 'd_', 'eco_', 'pr_', 'imp_', 'gear_'];  // ob_ also checkbox but listed separately
  var TAG_PREFIXES   = ['sp_', 'a_'];
  var PREFIX_ORDER   = ['b_', 'sb_', 'd_', 'eco_', 'pr_', 'imp_', 'gear_', 'sp_', 'a_', 'ob_', 'depth_'];

  var PREFIX_LABELS = {
    'b_':     'Ocean Basin',
    'sb_':    'Ocean Sub-basin',
    'd_':     'Discipline',
    'eco_':   'Ecosystem',
    'pr_':    'Pressure / Threat',
    'imp_':   'Impact / Response',
    'gear_':  'Fishing Gear',
    'sp_':    'Species',
    'a_':     'Analytical Techniques',
    'ob_':    'Ocean Basin (geographic)',
    'depth_': 'Depth'
  };

  var RULE_DOC_BASE = 'https://github.com/SimonDedman/elasmo_analyses/blob/main/docs/schema_proposals/';
  var PREFIX_RULE_DOCS = {
    'b_':     'ocean_basin_proposal.md',
    'sb_':    'ocean_basin_proposal.md',
    'd_':     'discipline_proposal.md',
    'eco_':   'ecosystem_component_proposal.md',
    'pr_':    'pressure_proposal.md',
    'imp_':   'impact_proposal.md',
    'gear_':  'gear_proposal.md',
    'sp_':    'species_proposal.md',
    'a_':     'analytical_techniques_proposal.md',
    'ob_':    'ocean_basin_proposal.md',
    'depth_': 'depth_proposal.md'
  };

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  var _state   = {};   // { [paperId]: { [prefix]: { rating, added, removed, notes, rule_suggestions, depth_min_m, depth_max_m } } }
  var _pageData = window.PAGE_DATA || {};
  var _storageKey = 'validate_' + (_pageData.openalex_id || 'unknown');
  var _sharedOptions = {};  // loaded from assets/options.json: { sp_: [...], a_: [...] }
  var _rules = {};  // loaded from assets/rules.json: { prefix: { col_name: { terms, threshold, anchors, ... } } }

  function _loadState() {
    try {
      var raw = localStorage.getItem(_storageKey);
      if (raw) { _state = JSON.parse(raw); }
    } catch (e) {
      console.warn('validate.js: could not load state from localStorage', e);
    }
  }

  function _saveState() {
    try {
      localStorage.setItem(_storageKey, JSON.stringify(_state));
    } catch (e) {
      console.warn('validate.js: could not save state to localStorage', e);
    }
  }

  function _ensureState(paperId, prefix) {
    if (!_state[paperId]) { _state[paperId] = {}; }
    if (!_state[paperId][prefix]) {
      _state[paperId][prefix] = {
        rating:           null,
        added:            [],
        removed:          [],
        notes:            '',
        rule_suggestions: { threshold: null, add_terms: [], remove_terms: [] },
        depth_min_m:      null,
        depth_max_m:      null
      };
    }
    return _state[paperId][prefix];
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function escapeHtml(text) {
    var d = document.createElement('div');
    d.textContent = String(text == null ? '' : text);
    return d.innerHTML;
  }

  function _shortAuthor(authorsStr) {
    if (!authorsStr) { return ''; }
    var parts = authorsStr.split(',');
    var first = parts[0].trim();
    // "Smith, J." → surname only
    var surname = first.split(' ')[0].replace(/[,;]$/, '');
    return parts.length > 1 ? surname + ' et al.' : surname;
  }

  function _truncate(str, max) {
    if (!str) { return ''; }
    return str.length > max ? str.slice(0, max - 1) + '\u2026' : str;
  }

  function _isPaperReviewed(paperId) {
    var paperState = _state[paperId];
    if (!paperState) { return false; }
    var prefixes = Object.keys(paperState);
    for (var i = 0; i < prefixes.length; i++) {
      if (paperState[prefixes[i]].rating) { return true; }
    }
    return false;
  }

  function _prefixFor(colName) {
    for (var i = 0; i < PREFIX_ORDER.length; i++) {
      if (colName.indexOf(PREFIX_ORDER[i]) === 0) { return PREFIX_ORDER[i]; }
    }
    return null;
  }

  // Sort prefixes: known order first, then alphabetically for unknowns
  function _sortPrefixes(prefixes) {
    return prefixes.slice().sort(function (a, b) {
      var ai = PREFIX_ORDER.indexOf(a);
      var bi = PREFIX_ORDER.indexOf(b);
      if (ai === -1 && bi === -1) { return a < b ? -1 : 1; }
      if (ai === -1) { return 1; }
      if (bi === -1) { return -1; }
      return ai - bi;
    });
  }

  // ---------------------------------------------------------------------------
  // Progress bar
  // ---------------------------------------------------------------------------

  function _updateProgress() {
    var papers  = _pageData.papers || {};
    var ids     = Object.keys(papers);
    var total   = ids.length;
    var reviewed = 0;
    for (var i = 0; i < ids.length; i++) {
      if (_isPaperReviewed(ids[i])) { reviewed++; }
    }
    var pct = total > 0 ? Math.round((reviewed / total) * 100) : 0;
    var bar  = document.getElementById('progress-bar-fill');
    var txt  = document.getElementById('progress-text');
    if (bar) { bar.style.width = pct + '%'; }
    if (txt) { txt.textContent = _t('progress', { reviewed: reviewed, total: total }); }
  }

  // ---------------------------------------------------------------------------
  // Evidence popover rendering
  // ---------------------------------------------------------------------------

  function _renderEvidence(evidenceArr) {
    if (!evidenceArr || evidenceArr.length === 0) {
      return '<span class="evidence-empty">No evidence recorded.</span>';
    }
    var html = '<ul class="evidence-list">';
    for (var i = 0; i < evidenceArr.length; i++) {
      var ev = evidenceArr[i];
      html += '<li>';
      html += '<span class="ev-terms">' + escapeHtml(ev.matched_terms || '') + '</span>';
      if (ev.section) {
        html += ' <span class="ev-section">[' + escapeHtml(ev.section) + ']</span>';
      }
      if (ev.total_freq != null) {
        html += ' <span class="ev-freq">freq:' + escapeHtml(ev.total_freq) + '</span>';
      }
      if (ev.threshold != null) {
        html += ' <span class="ev-thresh">thr:' + escapeHtml(ev.threshold) + '</span>';
      }
      if (ev.context) {
        html += '<blockquote class="ev-context">&hellip;' + escapeHtml(ev.context) + '&hellip;</blockquote>';
      }
      html += '</li>';
    }
    html += '</ul>';
    return html;
  }

  // ---------------------------------------------------------------------------
  // Rules palette (collapsible) — schema description + per-column rules
  // Tolerant of:
  //   - schema-level meta keys prefixed with "_" (e.g. _description, _criteria)
  //   - rules without terms/threshold (e.g. imp_direction uses sentiment cues)
  //   - schemas with no per-column rules at all (sb_/sp_/a_/ob_/depth_)
  // "columns" may be the triggered-column list (tier-1) or null (tag/depth).
  // ---------------------------------------------------------------------------

  function _renderRulesPalette(prefix, columns) {
    var prefixRules = _rules[prefix];
    if (!prefixRules || Object.keys(prefixRules).length === 0) { return ''; }

    // Separate schema-level meta keys (underscore-prefixed) from per-column rules
    var allKeys    = Object.keys(prefixRules);
    var metaKeys   = [];
    var ruleNames  = [];
    for (var ki = 0; ki < allKeys.length; ki++) {
      if (allKeys[ki].charAt(0) === '_') { metaKeys.push(allKeys[ki]); }
      else                               { ruleNames.push(allKeys[ki]); }
    }
    ruleNames.sort();

    // Summary: include rule count only when there are per-column rules
    var summaryParts = [];
    if (prefixRules._description) { summaryParts.push(escapeHtml(prefixRules._description)); }
    else                           { summaryParts.push('Extraction criteria'); }
    if (ruleNames.length > 0) { summaryParts.push('(' + ruleNames.length + ' rules)'); }

    var html = '<details class="rules-palette">';
    html += '<summary class="rules-palette-summary">Extraction rules &mdash; ' + summaryParts.join(' ') + '</summary>';
    html += '<div class="rules-palette-body">';

    // Schema-level criteria block
    if (prefixRules._description || prefixRules._criteria || prefixRules.source ||
        prefixRules._section_weights || prefixRules._proposal_url) {
      html += '<div class="rules-schema-meta">';
      if (prefixRules._description) {
        html += '<p class="rules-schema-desc">' + escapeHtml(prefixRules._description) + '</p>';
      }
      if (prefixRules._criteria) {
        html += '<p class="rules-schema-criteria"><strong>Assignation criteria:</strong> ' + escapeHtml(prefixRules._criteria) + '</p>';
      }
      if (prefixRules.column_count || prefixRules.storage) {
        html += '<p class="rules-schema-meta-extra">';
        if (prefixRules.column_count) {
          html += '<span class="rules-meta-chip">' + escapeHtml(String(prefixRules.column_count)) + ' columns</span>';
        }
        if (prefixRules.storage) {
          html += ' <span class="rules-meta-chip">' + escapeHtml(String(prefixRules.storage)) + '</span>';
        }
        html += '</p>';
      }
      // Section-weight table: which paper sections count most for this schema
      if (prefixRules._section_weights) {
        var sw = prefixRules._section_weights;
        var sectionOrder = ['TITLE','KEYWORDS','ABSTRACT','INTRODUCTION','METHODS','RESULTS','RESULTS_AND_DISCUSSION','DISCUSSION','CONCLUSIONS','OTHER'];
        html += '<div class="rules-section-weights"><strong>Section weighting:</strong>';
        html += '<table class="section-weights-table"><thead><tr>';
        for (var si = 0; si < sectionOrder.length; si++) {
          if (sw[sectionOrder[si]] != null) {
            html += '<th>' + escapeHtml(sectionOrder[si].replace(/_/g,' ')) + '</th>';
          }
        }
        html += '</tr></thead><tbody><tr>';
        for (var si2 = 0; si2 < sectionOrder.length; si2++) {
          if (sw[sectionOrder[si2]] != null) {
            var w = sw[sectionOrder[si2]];
            var wClass = w >= 2.0 ? 'w-max' : (w >= 1.0 ? 'w-high' : (w >= 0.5 ? 'w-med' : 'w-low'));
            html += '<td class="' + wClass + '">' + escapeHtml(String(w)) + '</td>';
          }
        }
        html += '</tr></tbody></table>';
        html += '<p class="section-weights-note">A keyword hit in a section is multiplied by its weight; a column fires when the weighted sum of hits ≥ its threshold.</p>';
        html += '</div>';
      }
      if (prefixRules.source) {
        html += '<p class="rules-schema-source"><em>Source: ' + escapeHtml(prefixRules.source) + '</em></p>';
      }
      if (prefixRules._proposal_url) {
        html += '<p class="rules-schema-proposal"><a href="' + escapeHtml(prefixRules._proposal_url) + '" target="_blank" rel="noopener">&#128196; Full schema proposal</a></p>';
      }
      html += '</div>';
    }

    // Per-column rules
    for (var ri = 0; ri < ruleNames.length; ri++) {
      var rn   = ruleNames[ri];
      var rule = prefixRules[rn];
      if (!rule || typeof rule !== 'object') { continue; }

      // Did this rule fire for this paper? (columns may be null for non-checkbox schemas)
      var fired = false;
      if (columns) {
        for (var ci = 0; ci < columns.length; ci++) {
          if (columns[ci].name === rn && columns[ci].triggered) { fired = true; break; }
        }
      }

      html += '<div class="rule-entry' + (fired ? ' rule-fired' : '') + '">';
      html += '<span class="rule-name">' + escapeHtml(rn.replace(prefix, '').replace(/_/g, ' ')) + '</span>';
      if (rule.threshold != null) {
        html += ' <span class="rule-threshold">thr:' + escapeHtml(String(rule.threshold)) + '</span>';
      }
      if (fired) { html += ' <span class="rule-badge-active">active</span>'; }

      if (rule.description) {
        html += '<p class="rule-description">' + escapeHtml(rule.description) + '</p>';
      }
      if (rule.method) {
        html += '<p class="rule-method"><em>Method:</em> ' + escapeHtml(rule.method) + '</p>';
      }

      if (Array.isArray(rule.terms) && rule.terms.length > 0) {
        html += '<div class="rule-terms">';
        for (var ti = 0; ti < rule.terms.length; ti++) {
          html += '<span class="rule-term">' + escapeHtml(rule.terms[ti]) + '</span>';
        }
        html += '</div>';
      }
      if (Array.isArray(rule.anchors) && rule.anchors.length > 0) {
        html += '<div class="rule-anchors">Anchors: ';
        for (var ai = 0; ai < rule.anchors.length; ai++) {
          html += '<span class="rule-anchor">' + escapeHtml(rule.anchors[ai]) + '</span>';
        }
        html += '</div>';
      }
      if (Array.isArray(rule.case_sensitive_terms) && rule.case_sensitive_terms.length > 0) {
        html += '<div class="rule-cs">Case-sensitive: ' + rule.case_sensitive_terms.map(escapeHtml).join(', ') + '</div>';
      }

      // Sentiment-cue lists (imp_direction)
      if (Array.isArray(rule.positive_cues) && rule.positive_cues.length > 0) {
        html += '<div class="rule-cues rule-cues-pos"><strong>Positive cues:</strong> ';
        html += rule.positive_cues.map(function (t) {
          return '<span class="rule-term">' + escapeHtml(t) + '</span>';
        }).join(' ');
        html += '</div>';
      }
      if (Array.isArray(rule.negative_cues) && rule.negative_cues.length > 0) {
        html += '<div class="rule-cues rule-cues-neg"><strong>Negative cues:</strong> ';
        html += rule.negative_cues.map(function (t) {
          return '<span class="rule-term">' + escapeHtml(t) + '</span>';
        }).join(' ');
        html += '</div>';
      }
      // Numeric-pattern lists (imp_quantified)
      if (Array.isArray(rule.patterns) && rule.patterns.length > 0) {
        html += '<div class="rule-patterns"><strong>Patterns matched:</strong><ul>';
        for (var pi = 0; pi < rule.patterns.length; pi++) {
          html += '<li>' + escapeHtml(rule.patterns[pi]) + '</li>';
        }
        html += '</ul></div>';
      }
      // Derivation logic steps
      if (Array.isArray(rule.logic) && rule.logic.length > 0) {
        html += '<div class="rule-logic"><strong>Logic:</strong><ul>';
        for (var li = 0; li < rule.logic.length; li++) {
          html += '<li>' + escapeHtml(rule.logic[li]) + '</li>';
        }
        html += '</ul></div>';
      }
      if (rule.source) {
        html += '<p class="rule-source"><em>Source: ' + escapeHtml(rule.source) + '</em></p>';
      }

      html += '</div>'; // .rule-entry
    }

    html += '</div>'; // .rules-palette-body
    html += '</details>';
    return html;
  }

  // ---------------------------------------------------------------------------
  // Rating + notes + rule feedback HTML (shared across category types)
  // ---------------------------------------------------------------------------

  function _renderRatingRow(paperId, prefix, isTier1) {
    var s      = _ensureState(paperId, prefix);
    var nameBase = 'rating_' + paperId + '_' + prefix;
    var ratings  = ['correct', 'partially_correct', 'incorrect'];
    var variants = ['correct', 'partial', 'incorrect'];  // CSS class variants
    var labels   = ['Correct', 'Partially correct', 'Incorrect'];

    var html = '<div class="rating-row" style="display:flex;align-items:center;gap:1rem;margin:0.5rem 0;">';
    html += '<span class="rating-label" style="font-weight:600;font-size:0.85rem;">Rating:</span>';
    for (var i = 0; i < ratings.length; i++) {
      var isSelected = s.rating === ratings[i];
      var checked    = isSelected ? ' checked' : '';
      var cls        = 'rating-option ' + variants[i] + (isSelected ? ' selected' : '');
      html += '<label class="' + cls + '">';
      html += '<input type="radio" name="' + escapeHtml(nameBase) + '"';
      html += ' value="' + ratings[i] + '"' + checked;
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' class="rating-radio">';
      html += ' ' + labels[i];
      html += '</label>';
    }
    if (s.changes_count != null) {
      html += '<span class="changes-count" style="font-size:0.75rem;color:#868e96;">(' + s.changes_count + ' change' + (s.changes_count !== 1 ? 's' : '') + ')</span>';
    }
    html += '</div>';

    // Notes
    html += '<div class="notes-row">';
    html += '<label class="notes-label">Notes:</label>';
    html += '<textarea class="notes-area"';
    html += ' data-paper="' + escapeHtml(paperId) + '"';
    html += ' data-prefix="' + escapeHtml(prefix) + '"';
    html += ' rows="2">' + escapeHtml(s.notes || '') + '</textarea>';
    html += '</div>';

    // Rule feedback only for Tier 1 checkbox categories (not sp_, a_, ob_, depth_)
    if (isTier1 && TIER1_CHECKBOX.indexOf(prefix) !== -1) {
      var rs = s.rule_suggestions;
      html += '<div class="rule-feedback">';
      html += '<span class="rule-label">Rule feedback:</span>';
      html += '<label class="rule-item">Threshold: ';
      html += '<input type="number" class="threshold-input"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' min="1" step="1" placeholder="current"';
      html += ' value="' + escapeHtml(rs.threshold != null ? String(rs.threshold) : '') + '">';
      html += ' <button class="btn-reset-threshold" data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' style="font-size:0.75rem;cursor:pointer;background:none;border:1px solid #ccc;border-radius:3px;padding:0 4px;">Reset</button>';
      html += '</label>';
      html += '<label class="rule-item">Add term: ';
      html += '<input type="text" class="add-term-input"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' placeholder="e.g. demersal">';
      html += '<button class="btn-add-term"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += '>+</button>';
      var addTermsList = rs.add_terms && rs.add_terms.length
        ? '<span class="term-tags">' + rs.add_terms.map(function (t) {
            return '<span class="term-tag add-tag">' + escapeHtml(t)
              + '<button class="btn-remove-added-term" data-paper="' + escapeHtml(paperId) + '"'
              + ' data-prefix="' + escapeHtml(prefix) + '"'
              + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
          }).join('') + '</span>'
        : '';
      html += addTermsList;
      html += '</label>';
      html += '<label class="rule-item">Remove term: ';
      html += '<input type="text" class="remove-term-input"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' placeholder="e.g. pelagic">';
      html += '<button class="btn-remove-term"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += '>+</button>';
      var removeTermsList = rs.remove_terms && rs.remove_terms.length
        ? '<span class="term-tags">' + rs.remove_terms.map(function (t) {
            return '<span class="term-tag remove-tag">' + escapeHtml(t)
              + '<button class="btn-delete-removed-term" data-paper="' + escapeHtml(paperId) + '"'
              + ' data-prefix="' + escapeHtml(prefix) + '"'
              + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
          }).join('') + '</span>'
        : '';
      html += removeTermsList;
      html += '</label>';
      html += '</div>';
    }

    return html;
  }

  // ---------------------------------------------------------------------------
  // Checkbox category (Tier1 + ob_)
  // ---------------------------------------------------------------------------

  function _renderCheckboxCategory(paperId, prefix, catData, isTier1) {
    var s       = _ensureState(paperId, prefix);
    var columns = catData.columns || [];
    var html    = '';

    html += '<div class="checkbox-grid">';
    for (var i = 0; i < columns.length; i++) {
      var col        = columns[i];
      var colName    = col.name || '';
      var triggered  = !!col.triggered;
      var isAdded    = s.added.indexOf(colName) !== -1;
      var isRemoved  = s.removed.indexOf(colName) !== -1;

      // Effective checked state: originally triggered + added − removed
      var effectiveChecked = (triggered && !isRemoved) || isAdded;
      var originalClass    = triggered ? ' original' : '';
      var addedClass       = isAdded   ? ' manually-added' : '';
      var removedClass     = isRemoved ? ' manually-removed' : '';

      var colId    = 'chk_' + paperId + '_' + colName;
      var label    = colName.replace(prefix, '').replace(/_/g, ' ');
      var evidence = col.evidence || [];

      // Optional derived summary value (e.g. imp_direction = "positive" /
      // "negative" / "mixed" / "not stated"). Tier B populates col.value on
      // the generator side; Tier A renders it gracefully when present.
      var colValue = (col.value != null && col.value !== '') ? String(col.value) : '';

      html += '<div class="checkbox-item' + originalClass + addedClass + removedClass + '">';
      html += '<label>';
      html += '<input type="checkbox" id="' + escapeHtml(colId) + '"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' data-col="' + escapeHtml(colName) + '"';
      html += ' data-original="' + (triggered ? '1' : '0') + '"';
      html += ' class="col-checkbox"';
      if (effectiveChecked) { html += ' checked'; }
      html += '>';
      html += ' ' + escapeHtml(label);
      if (colValue) {
        html += ' <span class="col-value col-value-' + escapeHtml(colValue.replace(/\s+/g, '-')) + '">=&nbsp;' + escapeHtml(colValue) + '</span>';
      }
      html += '</label>';

      // Show evidence (i) button whenever we have snippets OR a derived value
      // to display (meta summary columns have a value but no snippets).
      if (evidence.length > 0 || colValue) {
        html += ' <button class="btn-evidence" aria-label="Show evidence"';
        html += ' data-paper="' + escapeHtml(paperId) + '"';
        html += ' data-col="' + escapeHtml(colName) + '"';
        html += '>&#9432;</button>';
      }

      html += '</div>'; // .checkbox-item
    }
    html += '</div>'; // .checkbox-grid

    // Evidence panels rendered below the grid (full width). A panel is
    // rendered if the column has snippets OR a derived summary value
    // (e.g. imp_direction → "positive" / "negative" / "mixed" / "not stated").
    for (var j = 0; j < columns.length; j++) {
      var evCol   = columns[j];
      var evArr   = evCol.evidence || [];
      var evValue = (evCol.value != null && evCol.value !== '') ? String(evCol.value) : '';
      if (evArr.length === 0 && !evValue) { continue; }

      html += '<div class="evidence-panel" id="ev_' + escapeHtml(paperId) + '_' + escapeHtml(evCol.name) + '" hidden>';
      html += '<div class="evidence-panel-header">' + escapeHtml(evCol.name.replace(prefix, '').replace(/_/g, ' ')) + '</div>';
      if (evValue) {
        html += '<p class="evidence-value"><strong>Derived value:</strong> ';
        html += '<span class="col-value col-value-' + escapeHtml(evValue.replace(/\s+/g, '-')) + '">' + escapeHtml(evValue) + '</span>';
        html += '</p>';
      }
      if (evArr.length > 0) {
        html += _renderEvidence(evArr);
      } else {
        html += '<p class="evidence-empty-hint">No matched-term snippets recorded for this summary column. See the Extraction rules panel below for how the value is derived.</p>';
      }
      html += '</div>';
    }

    // Rules palette (collapsible, shows assignation criteria for this schema)
    html += _renderRulesPalette(prefix, columns);

    html += _renderRatingRow(paperId, prefix, isTier1);
    return html;
  }

  // ---------------------------------------------------------------------------
  // Tag category (sp_, a_)
  // ---------------------------------------------------------------------------

  function _renderTagCategory(paperId, prefix, catData) {
    var s           = _ensureState(paperId, prefix);
    var triggered   = catData.triggered   || [];
    var frequencies = catData.frequencies || {};
    var allOptions  = _sharedOptions[prefix] || [];

    // Effective tags: triggered minus removed plus added
    var effective = [];
    var i;
    for (i = 0; i < triggered.length; i++) {
      if (s.removed.indexOf(triggered[i]) === -1) {
        effective.push({ val: triggered[i], original: true });
      }
    }
    for (i = 0; i < s.added.length; i++) {
      if (triggered.indexOf(s.added[i]) === -1) {
        effective.push({ val: s.added[i], original: false });
      }
    }

    var html = '<div class="tag-section">';

    // Threshold / assignation summary — prefer the per-paper threshold embedded
    // in PAGE_DATA (catData.trigger_threshold), fall back to the rules.json
    // schema-level threshold, finally to any mention. This keeps the hint
    // correct for pages generated before/after the Tier B threshold change.
    var prefixRule = _rules[prefix];
    var threshold  = catData.trigger_threshold
                     || (prefixRule && prefixRule.trigger_threshold)
                     || 1;
    if (prefixRule && prefixRule._criteria) {
      var labelText = prefix === 'sp_' ? 'Species trigger'
                    : prefix === 'a_'  ? 'Technique trigger'
                    : 'Trigger rule';
      html += '<p class="tag-threshold-hint"><strong>' + labelText + ':</strong> ';
      html += 'frequency \u2265 ' + threshold;
      html += (threshold > 1
        ? ' (mentions below threshold are available in the "Add by occurrence" dropdown). '
        : ' \u2014 any mention counts. ');
      html += '<span class="tag-threshold-detail">Raw mention count in full PDF text; see Extraction rules below.</span></p>';
    }

    // Existing tags — include per-tag occurrence frequency where known.
    html += '<div class="tag-list" id="tags_' + escapeHtml(paperId) + '_' + escapeHtml(prefix) + '">';
    for (i = 0; i < effective.length; i++) {
      var tag      = effective[i];
      var tagLabel = tag.val.replace(prefix, '').replace(/_/g, ' ');
      var tagClass = tag.original ? 'tag original-tag' : 'tag added-tag';
      var tagFreq  = frequencies[tag.val];
      html += '<span class="' + tagClass + '">';
      html += escapeHtml(tagLabel);
      if (tagFreq != null && tagFreq > 0) {
        html += ' <span class="tag-freq-count">(' + tagFreq + '\u00d7)</span>';
      }
      html += '<button class="btn-remove-tag"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' data-val="' + escapeHtml(tag.val) + '"';
      html += ' aria-label="Remove ' + escapeHtml(tagLabel) + '">&times;</button>';
      html += '</span>';
    }
    html += '</div>'; // .tag-list

    // First dropdown: all options alphabetically (current behaviour)
    var selectId = 'ts_' + paperId + '_' + prefix.replace('_', '');
    var effectiveVals = effective.map(function (t) { return t.val; });
    html += '<select id="' + escapeHtml(selectId) + '"';
    html += ' class="tag-select"';
    html += ' data-paper="' + escapeHtml(paperId) + '"';
    html += ' data-prefix="' + escapeHtml(prefix) + '"';
    html += '>';
    html += '<option value="">Add ' + escapeHtml(PREFIX_LABELS[prefix] || prefix) + ' (alphabetical)&hellip;</option>';

    for (i = 0; i < allOptions.length; i++) {
      var opt = allOptions[i];
      if (effectiveVals.indexOf(opt) === -1) {
        var optLabel = opt.replace(prefix, '').replace(/_/g, ' ');
        html += '<option value="' + escapeHtml(opt) + '">' + escapeHtml(optLabel) + '</option>';
      }
    }
    html += '</select>';

    // Second dropdown (species only): options sorted by frequency descending
    if (prefix === 'sp_') {
      var frequencies = catData.frequencies || null;
      var freqSelectId = 'ts_' + paperId + '_spfreq';
      if (frequencies && Object.keys(frequencies).length > 0) {
        // Build list of species with freq > 0 that are not already in effective tags,
        // sorted by frequency descending
        var freqEntries = [];
        var freqKeys = Object.keys(frequencies);
        for (var fi = 0; fi < freqKeys.length; fi++) {
          var fk = freqKeys[fi];
          if (effectiveVals.indexOf(fk) === -1 && frequencies[fk] > 0) {
            freqEntries.push({ val: fk, freq: frequencies[fk] });
          }
        }
        freqEntries.sort(function (a, b) { return b.freq - a.freq; });

        html += '<select id="' + escapeHtml(freqSelectId) + '"';
        html += ' class="tag-select"';
        html += ' data-paper="' + escapeHtml(paperId) + '"';
        html += ' data-prefix="' + escapeHtml(prefix) + '"';
        html += ' data-freq="1"';
        html += '>';
        html += '<option value="">Add Species (by occurrence, &ge;1 mention)&hellip;</option>';
        for (var fei = 0; fei < freqEntries.length; fei++) {
          var fe = freqEntries[fei];
          var feLabel = fe.val.replace(prefix, '').replace(/_/g, ' ');
          html += '<option value="' + escapeHtml(fe.val) + '">' + escapeHtml(feLabel) + ' (' + fe.freq + ')</option>';
        }
        html += '</select>';
      } else {
        html += '<p class="tag-freq-unavailable" style="font-size:0.75rem;color:#868e96;margin:0.25rem 0 0;">';
        html += 'Frequency-sorted species dropdown not available — frequency data not yet generated.';
        html += '</p>';
      }
    }

    html += '</div>'; // .tag-section

    html += _renderRulesPalette(prefix, null);
    html += _renderRatingRow(paperId, prefix, false);
    return html;
  }

  // ---------------------------------------------------------------------------
  // Depth category
  // ---------------------------------------------------------------------------

  function _renderDepthCategory(paperId, catData) {
    var prefix = 'depth_';
    var s      = _ensureState(paperId, prefix);
    var range  = catData.depth_range  || '';
    var minVal = s.depth_min_m != null ? s.depth_min_m : (catData.depth_min_m != null ? catData.depth_min_m : '');
    var maxVal = s.depth_max_m != null ? s.depth_max_m : (catData.depth_max_m != null ? catData.depth_max_m : '');

    var html = '<div class="depth-section">';
    html += '<p class="depth-range-display">Extracted range: <strong>' + escapeHtml(range || 'not extracted') + '</strong></p>';
    html += '<div class="depth-inputs">';
    html += '<label>Min (m): <input type="number" class="depth-input depth-min"';
    html += ' data-paper="' + escapeHtml(paperId) + '" data-field="depth_min_m"';
    html += ' value="' + escapeHtml(String(minVal)) + '" step="1" min="0">';
    html += '</label>';
    html += '<label>Max (m): <input type="number" class="depth-input depth-max"';
    html += ' data-paper="' + escapeHtml(paperId) + '" data-field="depth_max_m"';
    html += ' value="' + escapeHtml(String(maxVal)) + '" step="1" min="0">';
    html += '</label>';
    html += '</div>';
    html += '</div>'; // .depth-section
    html += _renderRulesPalette(prefix, null);
    // No rating row for depth
    return html;
  }

  // ---------------------------------------------------------------------------
  // Paper block rendering
  // ---------------------------------------------------------------------------

  function _renderPaperBlock(paperId, paperData) {
    var meta       = paperData.meta       || {};
    var categories = paperData.categories || {};

    var year       = meta.year      || '';
    var title      = meta.title     || '(no title)';
    var authors    = meta.authors   || '';
    var journal    = meta.journal   || '';
    var doi        = meta.doi       || '';
    var studyType  = meta.study_type  || '';
    var country    = meta.country     || '';
    var superregion = meta.superregion || '';
    var epoch      = meta.epoch       || '';
    var altmetric  = meta.altmetric   || {};
    var altScore   = altmetric.alt_score || '';
    var oaStatus   = meta.oa_status   || '';
    var oaLicense  = meta.oa_license  || '';

    var shortAuth  = _shortAuthor(authors);
    var shortTitle = _truncate(title, 80);
    var reviewed   = _isPaperReviewed(paperId);
    var badgeClass = reviewed ? 'badge badge-reviewed' : 'badge badge-pending';
    var badgeText  = reviewed ? _t('reviewed') : _t('pending');

    // Gather and sort category prefixes
    var catPrefixes = Object.keys(categories);
    catPrefixes = _sortPrefixes(catPrefixes);

    // Separate known and dynamic prefixes
    var knownSet = {};
    PREFIX_ORDER.forEach(function (p) { knownSet[p] = true; });
    var dynamicPrefixes = catPrefixes.filter(function (p) { return !knownSet[p]; });

    var html = '<details class="paper-block" id="paper_' + escapeHtml(paperId) + '">';

    // Summary line
    html += '<summary class="paper-summary">';
    html += '<span class="paper-year">' + escapeHtml(String(year)) + '</span>';
    html += '<span class="paper-short-author">' + escapeHtml(shortAuth) + '</span>';
    html += '<span class="paper-title-short" title="' + escapeHtml(title) + '">' + escapeHtml(shortTitle) + '</span>';
    html += '<span class="paper-journal">' + escapeHtml(journal) + '</span>';
    html += '<span class="' + badgeClass + '" id="badge_' + escapeHtml(paperId) + '">' + badgeText + '</span>';
    html += '</summary>';

    // Paper body
    html += '<div class="paper-body">';

    // Metadata row
    html += '<div class="meta-row">';
    html += '<span class="meta-item"><strong>Year:</strong> ' + escapeHtml(String(year)) + '</span>';
    html += '<span class="meta-item"><strong>Journal:</strong> ' + escapeHtml(journal) + '</span>';
    if (doi) {
      html += '<span class="meta-item"><strong>DOI:</strong> <a href="https://doi.org/' + escapeHtml(doi) + '" target="_blank" rel="noopener">' + escapeHtml(doi) + '</a></span>';
    }
    if (studyType)   { html += '<span class="meta-item" title="Empirical, review, theoretical, etc."><strong>Study type:</strong> ' + escapeHtml(studyType) + '</span>'; }
    if (country)     { html += '<span class="meta-item"><strong>Country:</strong> '     + escapeHtml(country)     + '</span>'; }
    if (superregion) { html += '<span class="meta-item"><strong>Superregion:</strong> ' + escapeHtml(superregion) + '</span>'; }
    if (epoch)       { html += '<span class="meta-item" title="Geological time period of study specimens"><strong>Epoch:</strong> ' + escapeHtml(epoch) + '</span>'; }
    if (oaStatus) {
      var oaColour = oaStatus === 'gold' ? '#f59f00' : oaStatus === 'green' ? '#37b24d' : oaStatus === 'hybrid' ? '#f76707' : oaStatus === 'bronze' ? '#ae6c3c' : '#868e96';
      html += '<span class="meta-item" title="Open access status (from Unpaywall)"><strong>OA:</strong> <span style="color:' + oaColour + ';font-weight:600;">' + escapeHtml(oaStatus) + '</span>';
      if (oaLicense) { html += ' (' + escapeHtml(oaLicense) + ')'; }
      html += '</span>';
    }
    if (altScore) {
      var altNum = parseFloat(altScore);
      var altBin = altNum >= 500 ? 'exceptional' : altNum >= 100 ? 'very high' : altNum >= 50 ? 'high' : altNum >= 10 ? 'moderate' : altNum >= 1 ? 'low' : 'minimal';
      var altBinColour = altNum >= 500 ? '#e03131' : altNum >= 100 ? '#f76707' : altNum >= 50 ? '#f59f00' : altNum >= 10 ? '#37b24d' : '#868e96';
      var altTooltip = 'Altmetric attention score. Bins: minimal (<1), low (1-10), moderate (10-50), high (50-100), very high (100-500), exceptional (500+)';
      if (altmetric.alt_pct_journal) { altTooltip += '\\nJournal percentile: ' + altmetric.alt_pct_journal + '%'; }
      if (altmetric.alt_pct_all) { altTooltip += '\\nAll papers percentile: ' + altmetric.alt_pct_all + '%'; }
      html += '<span class="meta-item" title="' + escapeHtml(altTooltip) + '"><strong>Altmetric:</strong> ' + escapeHtml(altScore) + ' <span style="color:' + altBinColour + ';font-weight:600;">(' + altBin + ')</span></span>';
      // Altmetric breakdown
      var altParts = [];
      if (altmetric.alt_tweeters) { altParts.push('tweets:' + altmetric.alt_tweeters); }
      if (altmetric.alt_news) { altParts.push('news:' + altmetric.alt_news); }
      if (altmetric.alt_blogs) { altParts.push('blogs:' + altmetric.alt_blogs); }
      if (altmetric.alt_policy) { altParts.push('policy:' + altmetric.alt_policy); }
      if (altmetric.alt_wikipedia) { altParts.push('wiki:' + altmetric.alt_wikipedia); }
      if (altmetric.alt_mendeley) { altParts.push('Mendeley:' + altmetric.alt_mendeley); }
      if (altmetric.alt_pct_journal) { altParts.push('pct(journal):' + altmetric.alt_pct_journal + '%'); }
      if (altParts.length > 0) {
        html += '<span class="meta-item" style="font-size:0.75rem;color:#868e96;">' + altParts.join(' · ') + '</span>';
      }
    }
    html += '<span class="meta-item" title="Internal Shark References literature database ID"><strong>ID:</strong> ' + escapeHtml(String(paperId)) + '</span>';

    // SR habitat guesses (eco_1_guess, eco_2_guess, eco_3_guess)
    var g1 = meta.eco_1_guess, g2 = meta.eco_2_guess, g3 = meta.eco_3_guess;
    if (g1 || g2 || g3) {
      html += '<br><span class="meta-item" title="Shark References habitat classification (not rule-based extraction)"><strong>SR habitat:</strong> ';
      if (g1) { html += '<span class="sr-guess-tag">' + escapeHtml(g1) + '</span> '; }
      if (g2) { html += '<span class="sr-guess-tag">' + escapeHtml(g2) + '</span> '; }
      if (g3) { html += '<span class="sr-guess-tag">' + escapeHtml(g3) + '</span> '; }
      html += '</span>';
    }
    html += '</div>'; // .meta-row

    // Full authors
    if (authors) {
      html += '<div class="authors-row"><strong>Authors:</strong> ' + escapeHtml(authors) + '</div>';
    }

    // Categories: Tier 1 ordered, then Tier 2 ordered, then dynamic
    var orderedToRender = PREFIX_ORDER.concat(dynamicPrefixes);
    for (var i = 0; i < orderedToRender.length; i++) {
      var prefix = orderedToRender[i];
      var catData = categories[prefix];
      if (!catData) { continue; }

      var isCheckbox = TIER1_CHECKBOX.indexOf(prefix) !== -1 || prefix === 'ob_';
      var isTag      = TAG_PREFIXES.indexOf(prefix) !== -1;
      var isDepth    = prefix === 'depth_';
      var isTier1    = TIER1_CHECKBOX.indexOf(prefix) !== -1;

      var catLabel = PREFIX_LABELS[prefix] || prefix;
      var ruleDoc = PREFIX_RULE_DOCS[prefix];

      html += '<section class="cat-section" data-prefix="' + escapeHtml(prefix) + '">';
      html += '<h3 class="cat-title">' + escapeHtml(catLabel);
      if (ruleDoc) {
        html += ' <a href="' + RULE_DOC_BASE + ruleDoc + '" target="_blank" rel="noopener" ';
        html += 'style="font-size:0.75rem;font-weight:normal;color:#B6862C;text-decoration:underline;margin-left:0.5rem;" ';
        html += 'title="View the extraction rules for this schema">rules &#8599;</a>';
      }
      html += '</h3>';
      html += '<div class="cat-body">';

      if (isDepth) {
        html += _renderDepthCategory(paperId, catData);
      } else if (isTag) {
        html += _renderTagCategory(paperId, prefix, catData);
      } else if (isCheckbox) {
        html += _renderCheckboxCategory(paperId, prefix, catData, isTier1);
      } else {
        // Unknown/dynamic prefix with columns array — treat as checkbox
        if (catData.columns) {
          html += _renderCheckboxCategory(paperId, prefix, catData, false);
        } else if (catData.triggered) {
          html += _renderTagCategory(paperId, prefix, catData);
        }
      }

      html += '</div>'; // .cat-body
      html += '</section>';
    }

    html += '</div>'; // .paper-body
    html += '</details>';

    return html;
  }

  // ---------------------------------------------------------------------------
  // Render all papers
  // ---------------------------------------------------------------------------

  function _renderAll() {
    var container = document.getElementById('papers-container');
    if (!container) {
      console.error('validate.js: #papers-container not found');
      return;
    }

    var papers = _pageData.papers || {};
    var ids    = Object.keys(papers);

    // Sort by year descending, then id descending
    ids.sort(function (a, b) {
      var ya = parseInt((papers[a].meta || {}).year, 10) || 0;
      var yb = parseInt((papers[b].meta || {}).year, 10) || 0;
      if (yb !== ya) { return yb - ya; }
      return String(b).localeCompare(String(a));
    });

    var fragments = [];
    for (var i = 0; i < ids.length; i++) {
      fragments.push(_renderPaperBlock(ids[i], papers[ids[i]]));
    }
    container.innerHTML = fragments.join('');

    // Attach event handlers after DOM is ready
    _attachHandlers(container);

    // Init Tom Select for tag sections (deferred)
    requestAnimationFrame(function () {
      _initTomSelects(container);
    });

    _updateProgress();
  }

  // ---------------------------------------------------------------------------
  // Tom Select initialisation
  // ---------------------------------------------------------------------------

  function _initTomSelects(container) {
    if (typeof TomSelect === 'undefined') { return; }
    var selects = container.querySelectorAll('select.tag-select');
    for (var i = 0; i < selects.length; i++) {
      (function (sel) {
        var isFreqSelect = sel.dataset.freq === '1';
        new TomSelect(sel, {
          create:      false,
          placeholder: sel.options[0] ? sel.options[0].text : 'Add…',
          onItemAdd:   function (value) {
            var paperId = sel.dataset.paper;
            var prefix  = sel.dataset.prefix;
            _handleTagAdd(paperId, prefix, value);
            // Reset select
            this.clear();
            this.clearOptions();
            // Reload options minus current effective tags
            var s        = _ensureState(paperId, prefix);
            var catData  = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
            var triggered  = catData.triggered  || [];
            var effective  = triggered.filter(function (v) { return s.removed.indexOf(v) === -1; }).concat(s.added);
            var self       = this;
            if (isFreqSelect) {
              // Frequency-sorted dropdown: reload from catData.frequencies
              var frequencies = catData.frequencies || {};
              var freqEntries = [];
              var freqKeys = Object.keys(frequencies);
              for (var fi = 0; fi < freqKeys.length; fi++) {
                var fk = freqKeys[fi];
                if (effective.indexOf(fk) === -1 && frequencies[fk] > 0) {
                  freqEntries.push({ val: fk, freq: frequencies[fk] });
                }
              }
              freqEntries.sort(function (a, b) { return b.freq - a.freq; });
              freqEntries.forEach(function (fe) {
                self.addOption({
                  value: fe.val,
                  text: fe.val.replace(prefix, '').replace(/_/g, ' ') + ' (' + fe.freq + ')'
                });
              });
            } else {
              // Alphabetical dropdown: reload from allOptions
              var allOptions = _sharedOptions[prefix] || [];
              allOptions.forEach(function (opt) {
                if (effective.indexOf(opt) === -1) {
                  self.addOption({ value: opt, text: opt.replace(prefix, '').replace(/_/g, ' ') });
                }
              });
            }
            self.refreshOptions(false);
          }
        });
      })(selects[i]);
    }
  }

  // ---------------------------------------------------------------------------
  // Event delegation
  // ---------------------------------------------------------------------------

  function _attachHandlers(container) {

    // Checkbox toggle
    container.addEventListener('change', function (e) {
      var el = e.target;

      // Rating radio
      if (el.classList.contains('rating-radio')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.rating    = el.value;
        // Visual: mark the chosen label, clear its siblings
        var row = el.closest('.rating-row');
        if (row) {
          var opts = row.querySelectorAll('.rating-option');
          for (var oi = 0; oi < opts.length; oi++) {
            opts[oi].classList.remove('selected');
          }
          var chosen = el.closest('.rating-option');
          if (chosen) { chosen.classList.add('selected'); }
        }
        _saveState();
        _updateBadge(paperId);
        _updateProgress();
        return;
      }

      // Column checkbox
      if (el.classList.contains('col-checkbox')) {
        var paperId  = el.dataset.paper;
        var prefix   = el.dataset.prefix;
        var colName  = el.dataset.col;
        var original = el.dataset.original === '1';
        var s        = _ensureState(paperId, prefix);

        if (el.checked) {
          // User is checking: remove from removed list; add to added if not original
          var ri = s.removed.indexOf(colName);
          if (ri !== -1) { s.removed.splice(ri, 1); }
          if (!original && s.added.indexOf(colName) === -1) {
            s.added.push(colName);
          }
          el.parentElement.parentElement.classList.remove('manually-removed');
          if (!original) { el.parentElement.parentElement.classList.add('manually-added'); }
        } else {
          // User is unchecking: add to removed; remove from added if not original
          if (s.removed.indexOf(colName) === -1) { s.removed.push(colName); }
          if (!original) {
            var ai = s.added.indexOf(colName);
            if (ai !== -1) { s.added.splice(ai, 1); }
          }
          el.parentElement.parentElement.classList.add('manually-removed');
          el.parentElement.parentElement.classList.remove('manually-added');
        }
        // Update change count and auto-set rating
        s.changes_count = (s.added ? s.added.length : 0) + (s.removed ? s.removed.length : 0);
        if (!s.rating) {
          s.rating = s.changes_count > 0 ? 'partially_correct' : 'correct';
          // Update radio button display + highlight chosen option
          var radios = el.closest('.category-section').querySelectorAll('.rating-radio');
          for (var ri2 = 0; ri2 < radios.length; ri2++) {
            var isChosen = radios[ri2].value === s.rating;
            radios[ri2].checked = isChosen;
            var lbl = radios[ri2].closest('.rating-option');
            if (lbl) {
              if (isChosen) { lbl.classList.add('selected'); }
              else          { lbl.classList.remove('selected'); }
            }
          }
        }
        // Update changes count display
        var countSpan = el.closest('.category-section').querySelector('.changes-count');
        if (countSpan) {
          countSpan.textContent = '(' + s.changes_count + ' change' + (s.changes_count !== 1 ? 's' : '') + ')';
        }
        _saveState();
        _updateProgress();
        return;
      }

      // Notes textarea
      if (el.classList.contains('notes-area')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.notes     = el.value;
        _saveState();
        return;
      }

      // Threshold input
      if (el.classList.contains('threshold-input')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.rule_suggestions.threshold = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
        return;
      }

      // Depth inputs
      if (el.classList.contains('depth-input')) {
        var paperId = el.dataset.paper;
        var field   = el.dataset.field;
        var s       = _ensureState(paperId, 'depth_');
        s[field]    = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
        return;
      }
    });

    // Also listen for input event (notes textarea live save, threshold)
    container.addEventListener('input', function (e) {
      var el = e.target;
      if (el.classList.contains('notes-area')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.notes     = el.value;
        _saveState();
      }
      if (el.classList.contains('threshold-input')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.rule_suggestions.threshold = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
      }
      if (el.classList.contains('depth-input')) {
        var paperId = el.dataset.paper;
        var field   = el.dataset.field;
        var s       = _ensureState(paperId, 'depth_');
        s[field]    = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
      }
    });

    // Click delegation
    container.addEventListener('click', function (e) {
      var el = e.target;

      // Evidence toggle
      if (el.classList.contains('btn-evidence')) {
        var paperId = el.dataset.paper;
        var col     = el.dataset.col;
        var panel   = document.getElementById('ev_' + paperId + '_' + col);
        if (panel) {
          panel.hidden = !panel.hidden;
        }
        return;
      }

      // Remove tag
      if (el.classList.contains('btn-remove-tag')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var val     = el.dataset.val;
        _handleTagRemove(paperId, prefix, val);
        return;
      }

      // Add term button (rule feedback)
      if (el.classList.contains('btn-add-term')) {
        var paperId  = el.dataset.paper;
        var prefix   = el.dataset.prefix;
        var inputSel = '.add-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
        var input    = container.querySelector(inputSel);
        if (input && input.value.trim()) {
          var term = input.value.trim();
          var s    = _ensureState(paperId, prefix);
          if (s.rule_suggestions.add_terms.indexOf(term) === -1) {
            s.rule_suggestions.add_terms.push(term);
            _saveState();
            // Re-render rule feedback section inline
            _refreshRuleFeedback(container, paperId, prefix);
          }
          input.value = '';
        }
        return;
      }

      // Remove added term tag
      if (el.classList.contains('btn-remove-added-term')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var term    = el.dataset.term;
        var s       = _ensureState(paperId, prefix);
        var idx     = s.rule_suggestions.add_terms.indexOf(term);
        if (idx !== -1) { s.rule_suggestions.add_terms.splice(idx, 1); }
        _saveState();
        _refreshRuleFeedback(container, paperId, prefix);
        return;
      }

      // Remove term button (rule feedback)
      if (el.classList.contains('btn-remove-term')) {
        var paperId  = el.dataset.paper;
        var prefix   = el.dataset.prefix;
        var inputSel = '.remove-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
        var input    = container.querySelector(inputSel);
        if (input && input.value.trim()) {
          var term = input.value.trim();
          var s    = _ensureState(paperId, prefix);
          if (s.rule_suggestions.remove_terms.indexOf(term) === -1) {
            s.rule_suggestions.remove_terms.push(term);
            _saveState();
            _refreshRuleFeedback(container, paperId, prefix);
          }
          input.value = '';
        }
        return;
      }

      // Delete removed term tag
      if (el.classList.contains('btn-delete-removed-term')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var term    = el.dataset.term;
        var s       = _ensureState(paperId, prefix);
        var idx     = s.rule_suggestions.remove_terms.indexOf(term);
        if (idx !== -1) { s.rule_suggestions.remove_terms.splice(idx, 1); }
        _saveState();
        _refreshRuleFeedback(container, paperId, prefix);
        return;
      }

      // Reset threshold
      if (el.classList.contains('btn-reset-threshold')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.rule_suggestions.threshold = null;
        var inp = container.querySelector('.threshold-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]');
        if (inp) { inp.value = ''; }
        _saveState();
        return;
      }
    });

    // (native <details> disclosure triangle handles open/close indicator)
  }

  // ---------------------------------------------------------------------------
  // Tag helpers
  // ---------------------------------------------------------------------------

  function _handleTagAdd(paperId, prefix, value) {
    if (!value) { return; }
    var s = _ensureState(paperId, prefix);
    // If it was removed, un-remove it
    var ri = s.removed.indexOf(value);
    if (ri !== -1) { s.removed.splice(ri, 1); }
    // Add to added if not already in triggered or added
    var catData  = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
    var triggered = catData.triggered || [];
    if (triggered.indexOf(value) === -1 && s.added.indexOf(value) === -1) {
      s.added.push(value);
    }
    _saveState();
    _refreshTagSection(paperId, prefix);
  }

  function _handleTagRemove(paperId, prefix, value) {
    var s = _ensureState(paperId, prefix);
    var catData  = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
    var triggered = catData.triggered || [];

    if (triggered.indexOf(value) !== -1) {
      // Originally triggered: mark as removed
      if (s.removed.indexOf(value) === -1) { s.removed.push(value); }
    } else {
      // Manually added: remove from added
      var ai = s.added.indexOf(value);
      if (ai !== -1) { s.added.splice(ai, 1); }
    }
    _saveState();
    _refreshTagSection(paperId, prefix);
  }

  // Re-render just the tag list within a tag section (avoids full re-render)
  function _refreshTagSection(paperId, prefix) {
    var tagListEl = document.getElementById('tags_' + paperId + '_' + prefix);
    if (!tagListEl) { return; }

    var s         = _ensureState(paperId, prefix);
    var catData   = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
    var triggered = catData.triggered || [];

    var effective = [];
    var i;
    for (i = 0; i < triggered.length; i++) {
      if (s.removed.indexOf(triggered[i]) === -1) {
        effective.push({ val: triggered[i], original: true });
      }
    }
    for (i = 0; i < s.added.length; i++) {
      if (triggered.indexOf(s.added[i]) === -1) {
        effective.push({ val: s.added[i], original: false });
      }
    }

    var html = '';
    for (i = 0; i < effective.length; i++) {
      var tag      = effective[i];
      var tagLabel = tag.val.replace(prefix, '').replace(/_/g, ' ');
      var tagClass = tag.original ? 'tag original-tag' : 'tag added-tag';
      html += '<span class="' + tagClass + '">';
      html += escapeHtml(tagLabel);
      html += '<button class="btn-remove-tag"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' data-val="' + escapeHtml(tag.val) + '"';
      html += ' aria-label="Remove ' + escapeHtml(tagLabel) + '">&times;</button>';
      html += '</span>';
    }
    tagListEl.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // Rule feedback re-render helper (replaces just the .rule-feedback div)
  // ---------------------------------------------------------------------------

  function _refreshRuleFeedback(container, paperId, prefix) {
    var s  = _ensureState(paperId, prefix);
    var rs = s.rule_suggestions;

    // Rebuild just the term tag lists within the rule-feedback block
    // Add terms list
    var addSel  = '.add-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
    var addInput = container.querySelector(addSel);
    if (addInput) {
      var addTagContainer = addInput.parentElement.querySelector('.term-tags');
      if (!addTagContainer) {
        addTagContainer = document.createElement('span');
        addTagContainer.className = 'term-tags';
        addInput.parentElement.appendChild(addTagContainer);
      }
      addTagContainer.innerHTML = rs.add_terms.map(function (t) {
        return '<span class="term-tag add-tag">' + escapeHtml(t)
          + '<button class="btn-remove-added-term" data-paper="' + escapeHtml(paperId) + '"'
          + ' data-prefix="' + escapeHtml(prefix) + '"'
          + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
      }).join('');
    }

    // Remove terms list
    var removeSel   = '.remove-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
    var removeInput = container.querySelector(removeSel);
    if (removeInput) {
      var removeTagContainer = removeInput.parentElement.querySelector('.term-tags');
      if (!removeTagContainer) {
        removeTagContainer = document.createElement('span');
        removeTagContainer.className = 'term-tags';
        removeInput.parentElement.appendChild(removeTagContainer);
      }
      removeTagContainer.innerHTML = rs.remove_terms.map(function (t) {
        return '<span class="term-tag remove-tag">' + escapeHtml(t)
          + '<button class="btn-delete-removed-term" data-paper="' + escapeHtml(paperId) + '"'
          + ' data-prefix="' + escapeHtml(prefix) + '"'
          + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
      }).join('');
    }
  }

  // ---------------------------------------------------------------------------
  // Badge update
  // ---------------------------------------------------------------------------

  function _updateBadge(paperId) {
    var badge = document.getElementById('badge_' + paperId);
    if (!badge) { return; }
    var reviewed = _isPaperReviewed(paperId);
    badge.textContent  = reviewed ? _t('reviewed') : _t('pending');
    badge.className    = reviewed ? 'badge badge-reviewed' : 'badge badge-pending';
  }

  // ---------------------------------------------------------------------------
  // Author corrections helpers
  // ---------------------------------------------------------------------------

  function _getAuthorCorrections() {
    return _state.author_corrections || {};
  }

  function _setAuthorCorrection(field, original, corrected) {
    if (!_state.author_corrections) { _state.author_corrections = {}; }
    if (corrected === original || corrected === '') {
      // User reverted to original — remove the correction
      delete _state.author_corrections[field];
    } else {
      _state.author_corrections[field] = { original: original, corrected: corrected };
    }
    _saveState();
  }

  // ---------------------------------------------------------------------------
  // Author enrichment rendering (editable NamSor fields)
  // ---------------------------------------------------------------------------

  function _renderAuthorEnrichment(enrichEl, ns) {
    var ac = _getAuthorCorrections();
    var ci = _pageData.current_institution || {};
    var ehtml = '<div class="namsor-fields" style="display:flex;flex-wrap:wrap;gap:1rem;align-items:flex-start;">';

    // Current institution (editable text input, not a NamSor inference)
    var instVal = (ac.institution && ac.institution.corrected) ? ac.institution.corrected : (ci.name || '');
    var instOrig = ci.name || '';
    var locParts = [ci.city, ci.region, ci.country].filter(function (x) { return x; });
    var locStr = locParts.join(', ');
    ehtml += '<label style="display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem;min-width:18rem;">';
    ehtml += '<span title="Current institution from OpenAlex last_known_institutions"><strong>Institution</strong>';
    if (locStr) { ehtml += ' <span style="font-weight:normal;color:#868e96;">(' + escapeHtml(locStr) + ')</span>'; }
    ehtml += '</span>';
    ehtml += '<input type="text" id="current-institution" class="namsor-edit" data-field="institution" data-original="' + escapeHtml(instOrig) + '"';
    ehtml += ' value="' + escapeHtml(instVal) + '" placeholder="Current institution" style="width:100%;">';
    if (ac.institution) {
      ehtml += '<span class="namsor-orig-note">(originally: ' + escapeHtml(ac.institution.original) + ')</span>';
    }
    ehtml += '</label>';

    // Gender select
    var genderVal = (ac.gender && ac.gender.corrected) ? ac.gender.corrected : (ns.gender || '');
    var genderOrig = ns.gender || '';
    ehtml += '<label style="display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem;">';
    ehtml += '<span title="NamSor gender inference (probability: ' + escapeHtml(ns.gender_probability || '?') + ')"><strong>Gender*</strong></span>';
    ehtml += '<select id="namsor-gender" class="namsor-edit" data-field="gender" data-original="' + escapeHtml(genderOrig) + '">';
    var genderOptions = ['', 'M', 'F', 'Non-binary', 'Unknown'];
    var genderLabels  = ['— select —', 'M (male)', 'F (female)', 'Non-binary', 'Unknown'];
    for (var gi = 0; gi < genderOptions.length; gi++) {
      var gSel = genderVal === genderOptions[gi] ? ' selected' : '';
      ehtml += '<option value="' + escapeHtml(genderOptions[gi]) + '"' + gSel + '>' + escapeHtml(genderLabels[gi]) + '</option>';
    }
    ehtml += '</select>';
    if (ac.gender) {
      ehtml += '<span class="namsor-orig-note">(originally: ' + escapeHtml(ac.gender.original) + ')</span>';
    }
    ehtml += '</label>';

    // Origin country input with ISO2 datalist
    var originVal = (ac.origin_country && ac.origin_country.corrected) ? ac.origin_country.corrected : (ns.origin_country || '');
    var originOrig = ns.origin_country || '';
    ehtml += '<label style="display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem;">';
    ehtml += '<span title="NamSor inferred origin country"><strong>Origin country*</strong>';
    if (ns.origin_region) { ehtml += ' <span style="font-weight:normal;color:#868e96;">(' + escapeHtml(ns.origin_region) + ')</span>'; }
    ehtml += '</span>';
    ehtml += '<input type="text" id="namsor-origin" class="namsor-edit" data-field="origin_country" data-original="' + escapeHtml(originOrig) + '"';
    ehtml += ' list="origin-country-list" value="' + escapeHtml(originVal) + '" placeholder="ISO2 code" style="width:14rem;">';
    if (ac.origin_country) {
      ehtml += '<span class="namsor-orig-note">(originally: ' + escapeHtml(ac.origin_country.original) + ')</span>';
    }
    ehtml += '</label>';

    // Ethnicity input with datalist
    var ethVal = (ac.ethnicity && ac.ethnicity.corrected) ? ac.ethnicity.corrected : (ns.ethnicity || '');
    var ethOrig = ns.ethnicity || '';
    ehtml += '<label style="display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem;">';
    ehtml += '<span title="NamSor inferred ethnicity/diaspora"><strong>Ethnicity / diaspora*</strong></span>';
    ehtml += '<input type="text" id="namsor-ethnicity" class="namsor-edit" data-field="ethnicity" data-original="' + escapeHtml(ethOrig) + '"';
    ehtml += ' list="ethnicity-list" value="' + escapeHtml(ethVal) + '" placeholder="start typing..." style="width:14rem;">';
    if (ac.ethnicity) {
      ehtml += '<span class="namsor-orig-note">(originally: ' + escapeHtml(ac.ethnicity.original) + ')</span>';
    }
    ehtml += '</label>';

    ehtml += '</div>';
    ehtml += '<p style="margin:0.4rem 0 0;color:#868e96;font-size:0.75rem;">Corrections welcome. Changes saved automatically. *NamSor inference from name &amp; country only.</p>';

    // Datalists for autocomplete
    ehtml += '<datalist id="origin-country-list">';
    var isoCountries = ['AD','AE','AF','AG','AI','AL','AM','AO','AR','AS','AT','AU','AW','AX','AZ','BA','BB','BD','BE','BF','BG','BH','BI','BJ','BL','BM','BN','BO','BQ','BR','BS','BT','BV','BW','BY','BZ','CA','CC','CD','CF','CG','CH','CI','CK','CL','CM','CN','CO','CR','CU','CV','CW','CX','CY','CZ','DE','DJ','DK','DM','DO','DZ','EC','EE','EG','EH','ER','ES','ET','FI','FJ','FK','FM','FO','FR','GA','GB','GD','GE','GF','GG','GH','GI','GL','GM','GN','GP','GQ','GR','GS','GT','GU','GW','GY','HK','HM','HN','HR','HT','HU','ID','IE','IL','IM','IN','IO','IQ','IR','IS','IT','JE','JM','JO','JP','KE','KG','KH','KI','KM','KN','KP','KR','KW','KY','KZ','LA','LB','LC','LI','LK','LR','LS','LT','LU','LV','LY','MA','MC','MD','ME','MF','MG','MH','MK','ML','MM','MN','MO','MP','MQ','MR','MS','MT','MU','MV','MW','MX','MY','MZ','NA','NC','NE','NF','NG','NI','NL','NO','NP','NR','NU','NZ','OM','PA','PE','PF','PG','PH','PK','PL','PM','PN','PR','PS','PT','PW','PY','QA','RE','RO','RS','RU','RW','SA','SB','SC','SD','SE','SG','SH','SI','SJ','SK','SL','SM','SN','SO','SR','SS','ST','SV','SX','SY','SZ','TC','TD','TF','TG','TH','TJ','TK','TL','TM','TN','TO','TR','TT','TV','TW','TZ','UA','UG','UM','US','UY','UZ','VA','VC','VE','VG','VI','VN','VU','WF','WS','YE','YT','ZA','ZM','ZW'];
    for (var i = 0; i < isoCountries.length; i++) {
      ehtml += '<option value="' + isoCountries[i] + '">';
    }
    ehtml += '</datalist>';

    ehtml += '<datalist id="ethnicity-list">';
    var ethList = ['African','Anglo-Saxon','Arab','Armenian','Bengali','British','Burmese','Chinese','Dutch','Eastern-European','Filipino','French','German','Greek','Hispanic','Indian','Indo-Caribbean','Indonesian','Iranian','Irish','Italian','Japanese','Jewish','Korean','Lao-Thai','Malagasy','Malay','Mongolian','Nordic','Nubian','Pakistani','Persian','Polish','Polynesian','Portuguese','Russian','Scottish','Sikh','Somali','Sri-Lankan','Swedish','Swiss','Turkish','Ukrainian','Urdu','Uzbek','Vietnamese','Welsh'];
    for (var j = 0; j < ethList.length; j++) {
      ehtml += '<option value="' + ethList[j] + '">';
    }
    ehtml += '</datalist>';

    enrichEl.innerHTML = ehtml;

    // Attach change/input handlers
    var editEls = enrichEl.querySelectorAll('.namsor-edit');
    for (var ni = 0; ni < editEls.length; ni++) {
      (function (el) {
        var eventType = el.tagName === 'SELECT' ? 'change' : 'input';
        el.addEventListener(eventType, function () {
          _setAuthorCorrection(el.dataset.field, el.dataset.original, el.value.trim());
          // Update the "(originally: X)" note inline
          var note = el.parentElement.querySelector('.namsor-orig-note');
          var ac2  = _getAuthorCorrections();
          var corr = ac2[el.dataset.field];
          if (corr) {
            if (!note) {
              note = document.createElement('span');
              note.className = 'namsor-orig-note';
              el.parentElement.appendChild(note);
            }
            note.textContent = '(originally: ' + corr.original + ')';
          } else {
            if (note) { note.parentElement.removeChild(note); }
          }
        });
      })(editEls[ni]);
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  window.validateUI = {
    getState:    function () { return _state; },
    getPageData: function () { return _pageData; }
  };

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', function () {
    _loadState();
    // Render author enrichment (NamSor data) — editable fields
    var enrichEl = document.getElementById('author-enrichment');
    var ns = _pageData.namsor || {};
    if (enrichEl && (ns.gender || ns.origin_country || ns.ethnicity)) {
      _renderAuthorEnrichment(enrichEl, ns);
    } else if (enrichEl) {
      enrichEl.style.display = 'none';
    }

    // Load shared assets (options + rules) then render
    Promise.all([
      fetch('assets/options.json').then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }),
      fetch('assets/rules.json').then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }),
    ]).then(function (results) {
      _sharedOptions = results[0];
      _rules = results[1];
      _renderAll();
    });
  });

})();

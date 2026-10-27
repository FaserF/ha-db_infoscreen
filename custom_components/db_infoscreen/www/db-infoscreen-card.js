/**
 * DB-INFOSCREEN
 */

const LitElement = window.LitElement || Object.getPrototypeOf(customElements.get("ha-panel-lovelace"));
const { html, css } = LitElement.prototype;

const DEFAULT_COUNT = 6;

const TRANSLATIONS = {
  de: {
    initializing: "System wird initialisiert...",
    sentiment: "Stimmung",
    on_time: "Pünktlich",
    delayed: "Verspätet",
    cancelled: "AUSFALL",
    news_ticker: "LIVE BAHNHOFS-NEWS",
    scan_me: "REISEPLAN",
    insight_title: "Kontext-Check",
    insight_text: "AI berechnet hohe Stabilität für diese Verbindung.",
    action_coffee: "Brauche Kaffee",
    action_sync: "Exit-Sync",
    action_announce: "Ansage",
    action_share: "Teilen",
    sentiments: ["Chaos-Modus", "Frustriert", "In Ordnung", "Sehr entspannt"],
    tts_attention: "Achtung. Zug {train} nach {dest} heute auf Gleis {plat}.",
    editor_entity: "Sensor Entität",
    editor_weather: "Wetter Entität (für Effekte)",
    status_stable: "STABIL",
    status_congested: "ÜBERLASTET",
    share_message: "{train} nach {dest}: {time} (+{delay}m Verspätung)",
    share_clipboard_copied: "Details in die Zwischenablage kopiert",
    share_clipboard_failed: "Kopieren fehlgeschlagen"
  },
  en: {
    initializing: "Initializing system...",
    sentiment: "Sentiment",
    on_time: "On time",
    delayed: "Delayed",
    cancelled: "CANCELLED",
    news_ticker: "LIVE STATION NEWS",
    scan_me: "TRAVEL PLAN",
    insight_title: "Intelligence Insight",
    insight_text: "AI predicts high stability for this connection.",
    action_coffee: "Need Coffee",
    action_sync: "Exit-Sync",
    action_announce: "Announce",
    action_share: "Share",
    sentiments: ["Total Chaos", "Frustrated", "Neutral", "Very Relaxed"],
    tts_attention: "Attention. Train {train} to {dest} is on platform {plat}.",
    editor_entity: "Sensor Entity",
    editor_weather: "Weather Entity (for effects)",
    status_stable: "STABLE",
    status_congested: "CONGESTED",
    share_message: "{train} to {dest}: {time} ({delay}m delay)",
    share_clipboard_copied: "Trip details copied to clipboard",
    share_clipboard_failed: "Failed to copy trip details"
  }
};

class DBInfoscreenCard extends LitElement {
  constructor() {
    super();
    this._expandedRows = new Set();
    this._clockInterval = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._clockInterval = setInterval(() => this.requestUpdate(), 30000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._clockInterval) {
      clearInterval(this._clockInterval);
    }
  }

  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _expandedRows: { type: Object },
    };
  }

  _localize(key, dict = {}) {
    const lang = (this.hass.language || 'en').split('-')[0];
    const translations = TRANSLATIONS[lang] || TRANSLATIONS.en;
    let text = translations[key] || TRANSLATIONS.en[key] || key;

    Object.keys(dict).forEach(k => {
      text = text.replace(`{${k}}`, dict[k]);
    });
    return text;
  }

  static get styles() {
    return css`
      :host {
        --core-accent: #00d2ff;
        --core-bg: #000;
        --ontime: #34c759;
        --delay: #ff3b30;
      }
      ha-card {
        background: var(--core-bg); color: #fff; border-radius: 40px;
        border: 1px solid rgba(255, 255, 255, 0.1); overflow: hidden;
        font-family: 'Inter', -apple-system, system-ui, sans-serif;
        box-shadow: 0 40px 100px rgba(0,0,0,0.8); position: relative;
      }
      .weather-particles {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 0; overflow: hidden;
      }
      .particle { position: absolute; background: #fff; opacity: 0.5; top: -10%; animation: fall linear infinite; }
      @keyframes fall { to { transform: translateY(110vh); } }
      .header { padding: 45px; position: relative; z-index: 1; background: linear-gradient(180deg, rgba(20,20,20,0.8) 0%, transparent 100%); }
      .station-name { font-size: 3.5rem; font-weight: 950; letter-spacing: -4px; line-height: 0.8; margin-bottom: 15px; }
      .stats-bar { display: flex; gap: 20px; align-items: center; margin-top: 25px; }
      .stat-pill { background: rgba(255,255,255,0.05); padding: 8px 16px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: flex; align-items: center; gap: 8px; backdrop-filter: blur(10px); }
      .board-table { width: 100%; border-collapse: collapse; position: relative; z-index: 1; }
      .row { border-bottom: 1px solid rgba(255, 255, 255, 0.03); cursor: pointer; transition: 0.3s; }
      .row.ghost { opacity: 0.35; filter: grayscale(1); }
      .cell { padding: 25px 45px; }
      .line-badge { background: #fff; color: #000; padding: 4px 10px; border-radius: 6px; font-weight: 900; font-size: 0.8rem; min-width: 50px; text-align: center; }
      .line-ice { background: #ff3b30; color: #fff; }
      .dest-main { font-size: 1.3rem; font-weight: 800; display: block; }
      .dest-sub { font-size: 0.8rem; opacity: 0.4; }
      .time-v { font-family: monospace; font-size: 1.5rem; font-weight: 900; text-align: right; color: var(--core-accent); }
      .platform-v { width: 60px; height: 60px; border: 2px solid #fff; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; font-weight: 950; }
      .details-area { padding: 35px 45px 45px 120px; border-left: 8px solid var(--core-accent); background: rgba(255,255,255,0.02); }
      .context-actions { display: flex; gap: 15px; margin-top: 20px; }
      .action-btn { background: rgba(255,255,255,0.1); border: none; color: #fff; padding: 12px 18px; border-radius: 12px; font-weight: 800; cursor: pointer; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 10px; }
      .action-btn:hover { background: var(--core-accent); color: #000; }
      .footer { padding: 20px 45px; font-size: 0.6rem; opacity: 0.2; display: flex; justify-content: space-between; background: rgba(0,0,0,0.3); }
    `;
  }

  render() {
    if (!this.hass || !this.config) return html``;
    const stateObj = this.hass.states[this.config.entity];
    if (!stateObj) return html`<ha-card>${this._localize('initializing')}</ha-card>`;

    const departures = (stateObj.attributes.next_departures || []);
    const score = this._calcScore(departures);
    const sentiment = this._getSentiment(score);
    const weather = this.hass.states[this.config.weather_entity]?.state || 'sunny';

    return html`
      <ha-card>
        <div class="weather-particles">${this._renderParticles(weather)}</div>
        <div class="header">
          <div class="station-name">${stateObj.attributes.station}</div>
          <div class="stats-bar">
             <div class="stat-pill"><ha-icon icon="mdi:pulse"></ha-icon> ${score}%</div>
             <div class="stat-pill"><ha-icon icon="${sentiment.icon}"></ha-icon> ${sentiment.text}</div>
             <div class="stat-pill"><ha-icon icon="mdi:clock-outline"></ha-icon> ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
        </div>
        <table class="board-table">
          <tbody>${departures.slice(0, this.config.count || DEFAULT_COUNT).map((dep, idx) => this._renderRow(dep, idx))}</tbody>
        </table>
        <div class="footer">
          <span>v2026.FINAL // I18N SUPPORTED</span>
          <span>STATION STATUS: ${score > 80 ? this._localize('status_stable') : this._localize('status_congested')}</span>
        </div>
      </ha-card>
    `;
  }

  _renderRow(dep, idx) {
    const isGhost = dep.is_cancelled || dep.isCancelled;
    const tripId = dep.trip_id || `idx-${idx}`;
    const expanded = this._expandedRows.has(tripId);

    return html`
      <tr class="row ${isGhost ? 'ghost' : ''}" @click="${() => this._toggle(tripId)}">
        <td class="cell">
           <div style="display:flex; align-items:center; gap:20px">
              ${(() => {
                const trainLabel = (dep.train || dep.line || '').toString();
                return html`<span class="line-badge ${trainLabel.toLowerCase().includes('ice') ? 'line-ice' : ''}">${trainLabel}</span>`;
              })()}
              <div>
                 <span class="dest-main">${dep.destination}</span>
                 <span class="dest-sub">${isGhost ? this._localize('cancelled') : (dep.route ? 'via ' + dep.route.slice(0, 2).map(r => (r && r.name) || (typeof r === "string" ? r : "")).filter(Boolean).join(', ') : 'Direct')}</span>
              </div>
           </div>
        </td>
        <td class="cell" align="center"><div class="platform-v">${dep.platform || '—'}</div></td>
        <td class="cell">
           <div class="time-v">${dep.departure_current || dep.scheduledDeparture || '--:--'}</div>
           ${(() => {
             const delay = parseInt(dep.delay, 10);
             return (Number.isFinite(delay) && delay > 0) ? html`<div style="color:#ff3b30; text-align:right; font-weight:850; font-size:0.8rem">+${delay}’</div>` : '';
           })()}
        </td>
      </tr>
      ${expanded ? this._renderDetails(dep) : ''}
    `;
  }

  _renderDetails(dep) {
    const isLate = (dep.delay || 0) > 5;
    return html`
      <tr>
        <td colspan="3">
           <div class="details-area">
              <div style="font-size:0.75rem; text-transform:uppercase; color:rgba(255,255,255,0.4); margin-bottom:10px">${this._localize('insight_title')}</div>
              <div class="context-actions">
                 <button class="action-btn" @click="${() => this._runAction('exit_sync')}"><ha-icon icon="mdi:sync"></ha-icon> ${this._localize('action_sync')}</button>
                 ${isLate ? html`<button class="action-btn" @click="${() => this._runAction('coffee')}"><ha-icon icon="mdi:coffee"></ha-icon> ${this._localize('action_coffee')}</button>` : ''}
                 <button class="action-btn" @click="${() => this._announce(dep)}"><ha-icon icon="mdi:bullhorn"></ha-icon> ${this._localize('action_announce')}</button>
                 <button class="action-btn" @click="${() => this._share(dep)}"><ha-icon icon="mdi:share-variant"></ha-icon> ${this._localize('action_share')}</button>
              </div>
           </div>
        </td>
      </tr>
    `;
  }

  _renderParticles(weather) {
    const weatherStr = (typeof weather === 'string' ? weather : 'sunny').toLowerCase();
    if (!['rainy', 'snowy', 'pouring'].some(s => weatherStr.includes(s))) return html``;
    const isSnow = weatherStr.includes('snow');
    return Array.from({ length: 20 }).map(() => {
      const style = `left:${Math.random() * 100}%; animation-duration:${1 + Math.random() * 2}s; animation-delay:-${Math.random() * 5}s; width:${isSnow ? 5 : 1}px; height:${isSnow ? 5 : 15}px;`;
      return html`<div class="particle" style="${style}"></div>`;
    });
  }

  _getSentiment(score) {
    const texts = this._localize('sentiments');
    if (score > 90) return { icon: 'mdi:emoticon-excited-outline', text: texts[3] };
    if (score > 75) return { icon: 'mdi:emoticon-happy-outline', text: texts[2] };
    if (score > 50) return { icon: 'mdi:emoticon-neutral-outline', text: texts[1] };
    return { icon: 'mdi:emoticon-angry-outline', text: texts[0] };
  }

  _calcScore(deps) {
    if (!deps.length) return 100;
    return Math.round((deps.filter(d => (d.delay || 0) < 5).length / deps.length) * 100);
  }

  _runAction(type) {
    if (!this.config?.actions?.[type]) {
        console.warn(`[DB Infoscreen] No action configured for ${type}`);
        return;
    }
    const action = this.config.actions[type];
    if (typeof action.service !== 'string' || !action.service.includes('.')) {
        console.error(`[DB Infoscreen] Malformed service string in _runAction: ${action.service}`);
        return;
    }
    const [domain, service] = action.service.split('.');
    if (domain && service) {
        this.hass.callService(domain, service, action.data || {});
    }
  }

  _announce(dep) {
    if (typeof SpeechSynthesisUtterance === 'undefined' || !window.speechSynthesis) {
        console.warn("[DB Infoscreen] Speech synthesis not supported in this browser.");
        return;
    }
    try {
        const text = this._localize('tts_attention', { train: dep.train || '', dest: dep.destination || '', plat: dep.platform || '' });
        const sit = new SpeechSynthesisUtterance(text);
        const lang = this.hass.language || 'en';
        sit.lang = lang.includes('-') ? lang : (lang === 'de' ? 'de-DE' : 'en-US');
        window.speechSynthesis.speak(sit);
    } catch (e) {
        console.error("[DB Infoscreen] Announcement failed", e);
    }
  }

  _share(dep) {
    const text = this._localize('share_message', {
        train: dep.train || 'Train',
        dest: dep.destination || 'Destination',
        time: dep.departure_current || dep.scheduledDeparture || '',
        delay: dep.delay || 0
    });
    
    if (navigator.share) {
        navigator.share({ title: dep.train || 'DB', text: text });
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(text)
            .then(() => {
                this.hass.callService('persistent_notification', 'create', {
                    title: 'DB Infoscreen',
                    message: this._localize('share_clipboard_copied')
                });
            })
            .catch((err) => {
                console.error("[DB Infoscreen] Clipboard copy failed", err);
                this.hass.callService('persistent_notification', 'create', {
                    title: 'DB Infoscreen',
                    message: this._localize('share_clipboard_failed')
                });
            });
    }
  }

  _toggle(id) {
    const s = new Set(this._expandedRows);
    if (s.has(id)) s.delete(id); else s.add(id);
    this._expandedRows = s;
    this.requestUpdate();
  }

  setConfig(config) {
    if (!config || !config.entity) {
        throw new Error("Missing required 'entity' in card configuration");
    }
    this.config = config;
  }
  getCardSize() {
    return Math.ceil((this.config.count || DEFAULT_COUNT) * 1.5) + 1;
  }
  static getConfigElement() { return document.createElement("db-infoscreen-card-editor"); }
}

class DBInfoscreenCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object }
    };
  }
  setConfig(config) { this._config = config; }
  _localize(key) {
    const lang = (this.hass && this.hass.language ? this.hass.language : 'en').split('-')[0];
    return (TRANSLATIONS[lang] || TRANSLATIONS.en)[key] || key;
  }
  render() {
    if (!this.hass) return html``;
    const config = this._config || {};

    return html`<div style="padding:20px">
      <ha-textfield label="${this._localize('editor_entity')}" .value="${config.entity || ''}" @input="${this._changed}" .configValue="${'entity'}"></ha-textfield>
      <ha-textfield label="${this._localize('editor_weather')}" .value="${config.weather_entity || ''}" @input="${this._changed}" .configValue="${'weather_entity'}"></ha-textfield>
    </div>`;
  }
  _changed(ev) {
    this._config = { ...this._config, [ev.target.configValue]: ev.target.value };
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
  }
}

customElements.define("db-infoscreen-card-editor", DBInfoscreenCardEditor);
customElements.define("db-infoscreen-card", DBInfoscreenCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "db-infoscreen-card", name: "DB Infoscreen I18N EDITION", preview: true });

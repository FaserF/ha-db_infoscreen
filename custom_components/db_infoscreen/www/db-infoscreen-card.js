
/**
 * DB-Infoscreen Modern Departure Card (Premium Edition)
 * A state-of-the-art station-board style card for Home Assistant 2026.
 */

const LitElement = Object.getPrototypeOf(customElements.get("ha-panel-lovelace"));
const { html, css } = LitElement.prototype;

class DBInfoscreenCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
    };
  }

  static get styles() {
    return css`
      :host {
        --board-bg: var(--ha-card-background, var(--card-background-color, #111));
        --board-text: var(--primary-text-color, #fff);
        --accent-color: var(--primary-color, #03a9f4);
        --delay-color: #ff5252;
        --ontime-color: #4caf50;
        --platform-bg: rgba(255, 255, 255, 0.1);
        --glass-bg: rgba(255, 255, 255, 0.03);
        --row-hover: rgba(255, 255, 255, 0.08);
        display: block;
        transition: all 0.3s ease;
      }

      ha-card {
        overflow: hidden;
        background: var(--board-bg);
        color: var(--board-text);
        border-radius: var(--ha-card-border-radius, 16px);
        box-shadow: var(--ha-card-box-shadow, 0 8px 24px rgba(0, 0, 0, 0.3));
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
      }

      .header {
        padding: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, var(--accent-color) 0%, rgba(3, 169, 244, 0.8) 100%);
        color: white;
        cursor: pointer;
        position: relative;
        overflow: hidden;
      }

      .header::after {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect fill="white" fill-opacity="0.05" x="0" y="0" width="100" height="100"/></svg>');
        opacity: 0.1;
      }

      .header-title {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.8px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
      }

      .header-clock {
        font-family: 'SF Mono', 'JetBrains Mono', monospace;
        font-size: 1.3rem;
        font-weight: 600;
        background: rgba(0, 0, 0, 0.2);
        padding: 4px 12px;
        border-radius: 8px;
        letter-spacing: 1px;
      }

      .board-table {
        width: 100%;
        border-collapse: collapse;
      }

      .board-header {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: rgba(255, 255, 255, 0.4);
        background: rgba(0, 0, 0, 0.1);
      }

      .board-header th {
        padding: 14px 20px;
        text-align: left;
        font-weight: 700;
      }

      .departure-row {
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        animation: fadeIn 0.5s ease backwards;
      }

      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }

      .departure-row:hover {
        background: var(--row-hover);
        transform: scale(1.005);
        z-index: 10;
      }

      .departure-row.cancelled {
        text-decoration: line-through;
        opacity: 0.4;
        background: rgba(255, 82, 82, 0.05);
      }

      .departure-row td {
        padding: 18px 20px;
        vertical-align: middle;
      }

      .line-cell {
        width: 80px;
      }

      .line-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 5px 10px;
        border-radius: 6px;
        font-weight: 900;
        font-size: 0.85rem;
        min-width: 50px;
        text-transform: uppercase;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      }

      .line-s-bahn { color: #fff; background: #008d3f; }
      .line-r-bahn { color: #fff; background: #c00000; }
      .line-ice { color: #c00000; background: #fff; border: 2px solid #c00000; }
      .line-ic { color: #fff; background: #c00000; }
      .line-u-bahn { color: #fff; background: #00509b; }
      .line-bus { color: #fff; background: #9527b7; }

      .destination-cell {
        font-weight: 600;
        font-size: 1.15rem;
      }

      .destination-sub {
        display: block;
        font-size: 0.8rem;
        font-weight: 400;
        opacity: 0.5;
        margin-top: 2px;
      }

      .platform-cell {
        text-align: center;
        width: 60px;
      }

      .platform-num {
        background: var(--platform-bg);
        color: white;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: 800;
        border: 1px solid rgba(255, 255, 255, 0.15);
      }

      .time-cell {
        text-align: right;
        font-family: 'SF Mono', 'JetBrains Mono', monospace;
        font-size: 1.15rem;
        width: 100px;
      }

      .delay-indicator {
        font-size: 0.9rem;
        display: block;
        font-weight: 700;
        margin-top: 2px;
      }

      .delay-plus { 
        color: var(--delay-color);
        animation: pulse 2s infinite;
      }
      
      @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
      }

      .delay-ok { color: var(--ontime-color); opacity: 0.8; }

      .no-departures {
        padding: 60px 40px;
        text-align: center;
        opacity: 0.4;
        font-style: italic;
      }

      .footer {
        padding: 12px 20px;
        font-size: 0.7rem;
        opacity: 0.3;
        text-align: right;
        background: rgba(0, 0, 0, 0.1);
      }

      @media (max-width: 500px) {
        .board-header th:nth-child(3),
        .departure-row td:nth-child(3) {
          display: none;
        }
        .header-title { font-size: 1.3rem; }
        .destination-cell { font-size: 1.05rem; }
      }
    `;
  }

  render() {
    if (!this.hass || !this.config) return html``;

    const entityId = this.config.entity;
    const stateObj = this.hass.states[entityId];

    if (!stateObj) {
      return html`
        <ha-card>
          <div class="no-departures">Entity <b>${entityId}</b> not found.</div>
        </ha-card>
      `;
    }

    const departures = (stateObj.attributes.next_departures || []).filter(dep => dep.train || dep.line);
    const stationName = stateObj.attributes.station || stateObj.attributes.friendly_name || "Departure Board";
    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    return html`
      <ha-card>
        <div class="header" @click="${() => this._handleAction()}">
          <div class="header-title">${stationName}</div>
          <div class="header-clock">${currentTime}</div>
        </div>
        <table class="board-table">
          <thead>
            <tr class="board-header">
              <th>Line</th>
              <th>Destination</th>
              <th>Pl.</th>
              <th style="text-align: right">Time</th>
            </tr>
          </thead>
          <tbody>
            ${departures.length === 0 
              ? html`<tr><td colspan="4" class="no-departures">No upcoming departures found for this station.</td></tr>`
              : departures.slice(0, this.config.count || 10).map((dep, idx) => this._renderDeparture(dep, idx))
            }
          </tbody>
        </table>
        <div class="footer">
          DB-Infoscreen Modern UI &bull; ${stateObj.attributes.attribution || ''}
        </div>
      </ha-card>
    `;
  }

  _renderDeparture(dep, idx) {
    const isCancelled = dep.is_cancelled || dep.isCancelled;
    const trainName = dep.train || dep.line || "";
    const trainType = trainName.toLowerCase();
    
    let typeClass = "";
    if (trainType.startsWith("s ") || trainType.startsWith("s-")) typeClass = "line-s-bahn";
    else if (["re", "rb", "ire"].some(t => trainType.startsWith(t)) || trainType.includes("regional")) typeClass = "line-r-bahn";
    else if (trainType.includes("ice")) typeClass = "line-ice";
    else if (trainType.includes("ic")) typeClass = "line-ic";
    else if (trainType.startsWith("u ") || trainType.startsWith("u-")) typeClass = "line-u-bahn";
    else if (trainType.startsWith("bus")) typeClass = "line-bus";

    const delay = parseInt(dep.delay || 0);
    const scheduled = dep.time || dep.scheduledTime || dep.scheduledDeparture || "--:--";
    
    // Extract intermediate stops if detailed mode is on
    const via = dep.route ? dep.route.slice(0, 2).map(r => r.name || r).join(", ") : "";

    return html`
      <tr class="departure-row ${isCancelled ? 'cancelled' : ''}" style="animation-delay: ${idx * 50}ms">
        <td class="line-cell"><span class="line-badge ${typeClass}">${trainName}</span></td>
        <td class="destination-cell">
          ${dep.destination}
          ${via ? html`<span class="destination-sub">via ${via}</span>` : ''}
        </td>
        <td class="platform-cell"><span class="platform-num">${dep.platform || '—'}</span></td>
        <td class="time-cell">
          ${scheduled}
          ${delay > 0 
            ? html`<span class="delay-indicator delay-plus">+${delay}’</span>` 
            : delay === 0 && !isCancelled ? html`<span class="delay-indicator delay-ok">on time</span>` : ''
          }
          ${isCancelled ? html`<span class="delay-indicator delay-plus">CANCELLED</span>` : ''}
        </td>
      </tr>
    `;
  }

  _handleAction() {
    const event = new CustomEvent("hass-more-info", {
      detail: { entityId: this.config.entity },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  setConfig(config) {
    if (!config.entity) throw new Error("Please define an entity");
    this.config = config;
  }

  getCardSize() {
    return (this.config.count || 5) * 1.5 + 1;
  }
}

customElements.define("db-infoscreen-card", DBInfoscreenCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "db-infoscreen-card",
  name: "DB Infoscreen Card",
  preview: true,
  description: "A premium, station-board style card for train departures."
});

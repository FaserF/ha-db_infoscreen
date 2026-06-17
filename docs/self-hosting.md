# Self-Hosting 🐳

Hosting your own instance of the **DBF (DB-Fahrplan / db-fakedisplay)** backend API offers several benefits and is highly recommended for advanced setups.

---

## Why Host Your Own DBF Server?

Using the public API instance at `dbf.finalrewind.org` is convenient, but hosting your own instance has several major advantages:

1. **Bypass Integration Limits**: The integration limits you to **30 sensors** by default when using the public API to prevent overwhelming the public infrastructure. With a self-hosted instance, this limit is lifted.
2. **No Rate Limits or IP Bans**: The public API enforces a strict rate limit of 30 requests per minute total and 1 request per station per minute. If you have many sensors or short update intervals, you risk being temporarily or permanently rate-limited or IP-banned.
3. **Improved Reliability & Speed**: Your queries do not depend on the public API's availability and network latency, resulting in faster and more reliable sensor updates.
4. **Local Wagon Order Cache**: Self-hosted instances can download and cache wagon order diagrams locally.

---

## How to Host Your Own DBF Server

There are two primary ways to host the backend:

### 1. Home Assistant Add-on (Recommended for Home Assistant OS)

If you run Home Assistant OS or Supervised, you can install the DBF App as a local add-on.

* **Repository**: [FaserF/hassio-addons](https://github.com/FaserF/hassio-addons/tree/master/dbf)
* **Installation**:
  1. Go to **Settings** > **Add-ons** > **Add-on Store**.
  2. Click the three dots in the top-right and select **Repositories**.
  3. Add `https://github.com/FaserF/hassio-addons`.
  4. Find **DBF (DB-Infoscreen)** in the list and click **Install**.
  5. Start the add-on.
  6. Configure the integration to use your local IP/port (e.g., `http://192.168.1.50:8092`) as the **Custom API URL** in the integration settings.

### 2. Docker (Recommended for Container/Unraid setups)

The official backend `db-fakedisplay` is available as a Docker image.

* **GitHub Repository**: [derf/db-fakedisplay](https://github.com/derf/db-fakedisplay)
* **Run command**:
  ```bash
  docker run -d -p 8092:8092 derf/db-fakedisplay:latest
  ```
* Once running, point the **Custom API URL** in your integration configuration to `http://<your-docker-host-ip>:8092`.

---

## Rate Limits & Data Sources on Self-Hosted Instances

### Where does the data come from?

Even on a self-hosted instance, the server does not generate train data itself. Instead, the backend connects directly to the official transit APIs:

* **Deutsche Bahn IRIS-TTS**: An XML-based API providing real-time departure boards and train paths for Deutsche Bahn stations.
* **Local HAFAS/EFA APIs**: The official APIs of the respective regional transport networks (e.g., RMV, VRN, KVV).
* **DB Wagon Order API**: For fetching wagon arrangements.

### What are the rate limits when self-hosted?

* **To the Backend**: There are **no rate limits** between your Home Assistant instance and your self-hosted DBF server, as they run on your local network or private server.
* **To the Upstream APIs (DB, HAFAS)**: The self-hosted server queries the official APIs directly. Because these public interfaces are designed to handle millions of queries daily from official passenger apps, your single home setup querying every few minutes will not trigger any rate limits or bans from Deutsche Bahn.

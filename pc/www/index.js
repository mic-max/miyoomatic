const queue = document.getElementById("queue");
const tbody = document.getElementById("encounter-tbody");
const encounterCountEl = document.getElementById("encounter-count");
const maxSize = 10;

// Mutable so the dropdown can change which location we're viewing.
// TODO: populate the dropdown from a locations API and wire its onchange to setLocation().
let currentLoc = 99;
let currentMethod = 0;

// Cache /spawns responses by "loc-method". Each entry is the API payload:
// { "<pokedex_id>": { name, levels: [{level, odds}], genders } }
const spawnsCache = {};

async function loadSpawnsFor(loc, method) {
    const key = `${loc}-${method}`;
    if (spawnsCache[key]) return spawnsCache[key];
    const res = await fetch(`/spawns/${loc}/${method}`);
    if (!res.ok) throw new Error(`Spawns fetch failed: ${res.status}`);
    spawnsCache[key] = await res.json();
    return spawnsCache[key];
}

async function setLocation(loc, method) {
    currentLoc = loc;
    currentMethod = method;
    await loadSpawnsFor(loc, method);
    renderTable();
}

const STORAGE_KEY = "miyoomatic:stats";

function loadAllStats() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch { return {}; }
}

function saveAllStats(s) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

function locKey(loc, method) { return `${loc}-${method}`; }

function getLocStats(loc, method) {
    return loadAllStats()[locKey(loc, method)] || {counts: {}, shinies: []};
}

function setLocStats(loc, method, stats) {
    const all = loadAllStats();
    all[locKey(loc, method)] = stats;
    saveAllStats(all);
}

function recordEncounter(loc, method, pokedexId, level, gender, isShiny, encounterId) {
    const stats = getLocStats(loc, method);
    const key = `${pokedexId}-${level}`;
    if (!stats.counts[key]) stats.counts[key] = {m: 0, f: 0, u: 0};
    const slot = stats.counts[key];
    if (gender === true) slot.m++;
    else if (gender === false) slot.f++;
    else slot.u++;
    if (isShiny) {
        stats.shinies.push({
            pokedex_id: pokedexId,
            level,
            gender: gender === true ? "m" : gender === false ? "f" : "u",
            encounter_id: encounterId ?? null,
            timestamp: Date.now(),
        });
    }
    setLocStats(loc, method, stats);
}

function clearLocation(loc, method) {
    const all = loadAllStats();
    delete all[locKey(loc, method)];
    saveAllStats(all);
}

function totalAtLocation(stats) {
    let t = 0;
    for (const s of Object.values(stats.counts)) t += s.m + s.f + s.u;
    return t;
}

function countsFor(stats, pokedexId, level) {
    return stats.counts[`${pokedexId}-${level}`] || {m: 0, f: 0, u: 0};
}

async function randomEncounter() {
    // Server picks weighted-randomly and broadcasts via WS; we receive it in ws.onmessage.
    const res = await fetch(`/encounters/random/${currentLoc}/${currentMethod}`, {method: "POST"});
    if (!res.ok) console.error(`random encounter failed: ${res.status}`);
}

const audioPlayer = document.getElementById("music");
audioPlayer.volume = 0.05;

// Pokemon.Gender enum values from pc/src/Pokemon.py: UNKNOWN=1, MALE=2, FEMALE=3.
// addItem expects gender as: true=male, false=female, null=unknown.
function genderFromValue(v) {
    if (v === 2) return true;
    if (v === 3) return false;
    return null;
}

let ws = null;
let sessionId = null;
let reconnectDelay = 500;

function connectWS() {
    ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onopen = () => { reconnectDelay = 500; };
    ws.onmessage = (event) => {
        let msg;
        try { msg = JSON.parse(event.data); } catch { return; }
        if (msg.type === "hello") {
            // First hello: remember the server's session id.
            // Any later hello with a different id means the server restarted — reload to pick up
            // new HTML/JS/CSS (uvicorn --reload watches www/, so it restarts on those edits too).
            if (sessionId === null) sessionId = msg.session_id;
            else if (sessionId !== msg.session_id) location.reload();
            return;
        }
        if (msg.type === "encounter") {
            // Always persist the count to the encounter's own location, but only animate the
            // queue if the user is currently viewing that location.
            recordEncounter(msg.location_id, msg.method_id, msg.pokedex_id, msg.level,
                            genderFromValue(msg.gender), !!msg.is_shiny, msg.encounter_id);
            if (msg.location_id === currentLoc && msg.method_id === currentMethod) {
                addItem(msg.pokedex_id, msg.level, genderFromValue(msg.gender), !!msg.is_shiny);
            }
        }
    };
    ws.onclose = () => {
        setTimeout(connectWS, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 1.5, 5000);
    };
}
connectWS();

function clearEncounterRun() {
    const stats = getLocStats(currentLoc, currentMethod);
    if (totalAtLocation(stats) === 0) {
        console.log("Nothing to clear.");
        return;
    }
    clearLocation(currentLoc, currentMethod);
    renderTable();
    // TODO: snapshot the cleared run to a history table before deleting.
}

function pctText(part, whole) {
    if (whole === 0) return "0.00%";
    return (part / whole * 100).toFixed(2) + "%";
}

function renderTable() {
    const stats = getLocStats(currentLoc, currentMethod);
    const total = totalAtLocation(stats);
    encounterCountEl.textContent = total;
    tbody.innerHTML = "";

    const spawns = spawnsCache[locKey(currentLoc, currentMethod)];
    if (!spawns) return;  // first paint before /spawns has loaded — setLocation will re-render.

    for (const [pidStr, pokemon] of Object.entries(spawns)) {
        const pokedexId = parseInt(pidStr, 10);
        const levels = pokemon.levels.map(r => r.level);

        const tr = document.createElement("tr");
        const td = document.createElement("td");
        const rowspan = levels.length == 1 ? 2 : levels.length + 2;
        td.setAttribute("rowspan", rowspan);
        tr.appendChild(td);

        const div = document.createElement("div");
        div.className = "pokemon";
        td.appendChild(div);
        const sprite = document.createElement("img");
        sprite.className = "sprite";
        sprite.src = `img/pokemon/${String(pokedexId).padStart(3, "0")}.png`;
        const name = document.createElement("p");
        name.innerText = pokemon.name;
        div.appendChild(sprite);
        div.appendChild(name);
        // TODO: render type icons once a pokemon-info API exposes them.
        tbody.appendChild(tr);

        let totalM = 0, totalF = 0, totalU = 0;
        for (const level of levels) {
            const c = countsFor(stats, pokedexId, level);
            totalM += c.m; totalF += c.f; totalU += c.u;
            const rowSum = c.m + c.f + c.u;

            const lvlTr = document.createElement("tr");
            const tdLevel = document.createElement("td");
            tdLevel.innerText = level;
            const tdMales = document.createElement("td");
            tdMales.innerText = c.m;
            tdMales.dataset.cell = `${pokedexId}-${level}-m`;
            const tdFemales = document.createElement("td");
            tdFemales.innerText = c.f;
            tdFemales.dataset.cell = `${pokedexId}-${level}-f`;
            const tdOdds = document.createElement("td");
            tdOdds.innerText = pctText(rowSum, total);
            lvlTr.append(tdLevel, tdMales, tdFemales, tdOdds);
            tbody.appendChild(lvlTr);
        }

        if (levels.length > 1) {
            const sumRow = totalM + totalF + totalU;
            const trTotal = document.createElement("tr");
            const tdTotal = document.createElement("td");
            tdTotal.innerText = "Total";
            const tdM = document.createElement("td");
            tdM.innerText = totalM;
            const tdF = document.createElement("td");
            tdF.innerText = totalF;
            const tdOdds = document.createElement("td");
            tdOdds.innerText = pctText(sumRow, total);
            trTotal.append(tdTotal, tdM, tdF, tdOdds);
            tbody.appendChild(trTotal);
        }
    }
}

setLocation(currentLoc, currentMethod);

function makeEmptySlot() {
    const slot = document.createElement("div");
    slot.className = "slot empty";
    return slot;
}

function makeFilledSlot(pokedexId, number, gender, isShiny) {
    const slot = document.createElement("div");
    slot.className = "slot";

    const num = document.createElement("div");
    num.className = "number";
    if (gender !== null) num.classList.add(gender ? "male" : "female");
    num.textContent = number;

    const img = document.createElement("img");
    const prefix = isShiny ? "-" : "";
    img.src = `img/pokemon/${prefix}${String(pokedexId).padStart(3, "0")}.png`;

    slot.appendChild(num);
    slot.appendChild(img);
    return slot;
}

// Start with maxSize empty slots, never below.
for (let i = 0; i < maxSize; i++) queue.appendChild(makeEmptySlot());

let sliding = false;
const pending = [];

function addItem(pokedexId, level, gender, isShiny = false) {
    pending.push([pokedexId, level, gender, isShiny]);
    drainPending();
}

function drainPending() {
    if (sliding || pending.length === 0) return;
    const [pokedexId, level, gender, isShiny] = pending.shift();

    // recordEncounter was already called from ws.onmessage so localStorage is up to date.
    renderTable();

    const genderKey = gender === true ? "m" : gender === false ? "f" : null;
    if (genderKey) {
        const cell = tbody.querySelector(`td[data-cell="${pokedexId}-${level}-${genderKey}"]`);
        if (cell) cell.classList.add("flash");
    }

    // Append the new (11th) slot off the right edge of the visible area.
    queue.appendChild(makeFilledSlot(pokedexId, level, gender, isShiny));
    void queue.offsetWidth;

    sliding = true;
    queue.classList.add("sliding");

    const onDone = () => {
        queue.removeEventListener("transitionend", onDone);
        queue.classList.remove("sliding");
        queue.removeChild(queue.firstElementChild); // drop the oldest (leftmost) slot
        sliding = false;
        drainPending();
    };
    queue.addEventListener("transitionend", onDone);
}

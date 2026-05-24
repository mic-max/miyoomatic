const queue = document.getElementById("queue");
const tbody = document.getElementById("encounter-tbody");
const encounterCountEl = document.getElementById("encounter-count");
const maxSize = 10;

// TODO: drive these from the location dropdown.
const LOCATION_ID = 99;
const METHOD_ID = 0;

// Per-location/method roster: which pokemon/levels are possible here. Counts/odds are
// derived live from localStorage; this only carries metadata not in the DB (types).
// TODO: pull pokedex_id + levels from /spawns, drop the duplication here.
const LOCATION_ROSTERS = {
    "99-0": [
        {pokedex_id: 92,  name: "Gastly",  types: ["ghost", "poison"], levels: [13, 14, 15, 16, 17, 18, 19]},
        {pokedex_id: 104, name: "Cubone",  types: ["ground"],          levels: [15, 17]},
        {pokedex_id: 93,  name: "Haunter", types: ["ghost", "poison"], levels: [25]},
    ],
};

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
    const res = await fetch(`/encounters/random/${LOCATION_ID}/${METHOD_ID}`, {method: "POST"});
    if (!res.ok) console.error(`random encounter failed: ${res.status}`);
}

const timer = document.getElementById("timer");

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
            addItem(msg.pokedex_id, msg.level, genderFromValue(msg.gender), !!msg.is_shiny, msg.encounter_id);
        }
    };
    ws.onclose = () => {
        setTimeout(connectWS, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 1.5, 5000);
    };
}
connectWS();

function clearEncounterRun() {
    const stats = getLocStats(LOCATION_ID, METHOD_ID);
    if (totalAtLocation(stats) === 0) {
        console.log("Nothing to clear.");
        return;
    }
    clearLocation(LOCATION_ID, METHOD_ID);
    countDownDate = new Date().getTime();
    renderTable();
    // TODO: snapshot the cleared run to a history table before deleting.
}

 var countDownDate = new Date("Feb 2, 1997 15:37:25").getTime();

// Update the count down every 1 second
var x = setInterval(function() {
    // Get today's date and time
    var now = new Date().getTime();

    // Find the distance between now and the count down date
    var distance = now - countDownDate;

    // Time calculations for days, hours, minutes and seconds
    var days = Math.floor(distance / (1000 * 60 * 60 * 24));
    var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    var seconds = Math.floor((distance % (1000 * 60)) / 1000);

    let timerString = "";
    if (days > 0) {
        timerString += `${days}d `;
    }
    if (days > 0 || hours > 0) {
        timerString += `${hours}h `;
    }
    timerString += `${minutes}m ${seconds}s `;
    timer.innerHTML = timerString;
}, 1000);

function pctText(part, whole) {
    if (whole === 0) return "0.00%";
    return (part / whole * 100).toFixed(2) + "%";
}

function renderTable() {
    const stats = getLocStats(LOCATION_ID, METHOD_ID);
    const total = totalAtLocation(stats);
    encounterCountEl.textContent = total;
    tbody.innerHTML = "";

    const roster = LOCATION_ROSTERS[locKey(LOCATION_ID, METHOD_ID)] || [];
    for (const pokemon of roster) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        const rowspan = pokemon.levels.length == 1 ? 2 : pokemon.levels.length + 2;
        td.setAttribute("rowspan", rowspan);
        tr.appendChild(td);

        const div = document.createElement("div");
        div.className = "pokemon";
        td.appendChild(div);
        const sprite = document.createElement("img");
        sprite.className = "sprite";
        sprite.src = `img/pokemon/${String(pokemon.pokedex_id).padStart(3, "0")}.png`;
        const name = document.createElement("p");
        name.innerText = pokemon.name;
        div.appendChild(sprite);
        div.appendChild(name);
        const typesDiv = document.createElement("div");
        typesDiv.className = "types";
        div.appendChild(typesDiv);
        for (const type of pokemon.types) {
            const t = document.createElement("img");
            t.src = `img/types/${type}.png`;
            typesDiv.appendChild(t);
        }
        tbody.appendChild(tr);

        let totalM = 0, totalF = 0, totalU = 0;
        for (const level of pokemon.levels) {
            const c = countsFor(stats, pokemon.pokedex_id, level);
            totalM += c.m; totalF += c.f; totalU += c.u;
            const rowSum = c.m + c.f + c.u;

            const lvlTr = document.createElement("tr");
            const tdLevel = document.createElement("td");
            tdLevel.innerText = level;
            const tdMales = document.createElement("td");
            tdMales.innerText = c.m;
            tdMales.dataset.cell = `${pokemon.pokedex_id}-${level}-m`;
            const tdFemales = document.createElement("td");
            tdFemales.innerText = c.f;
            tdFemales.dataset.cell = `${pokemon.pokedex_id}-${level}-f`;
            const tdOdds = document.createElement("td");
            tdOdds.innerText = pctText(rowSum, total);
            lvlTr.append(tdLevel, tdMales, tdFemales, tdOdds);
            tbody.appendChild(lvlTr);
        }

        if (pokemon.levels.length > 1) {
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

renderTable();

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

function addItem(pokedexId, level, gender, isShiny = false, encounterId = null) {
    pending.push([pokedexId, level, gender, isShiny, encounterId]);
    drainPending();
}

function drainPending() {
    if (sliding || pending.length === 0) return;
    const [pokedexId, level, gender, isShiny, encounterId] = pending.shift();

    recordEncounter(LOCATION_ID, METHOD_ID, pokedexId, level, gender, isShiny, encounterId);
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

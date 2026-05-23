const queue = document.getElementById("queue");
const tbody = document.getElementById("encounter-tbody");
const maxSize = 10;
let encounters = 5142;
gastly_total = Math.round(encounters * 0.9)

// TODO: drive these from the location dropdown.
const LOCATION_ID = 99;
const METHOD_ID = 0;

let spawnTable = null;  // [{pokedex_id, level, odds}, ...] flattened from /spawns

async function loadSpawns() {
    const res = await fetch(`/spawns/${LOCATION_ID}/${METHOD_ID}`);
    if (!res.ok) throw new Error(`Spawns fetch failed: ${res.status}`);
    const data = await res.json();
    const flat = [];
    for (const [pid, p] of Object.entries(data)) {
        for (const row of p.levels) {
            flat.push({pokedex_id: parseInt(pid, 10), level: row.level, odds: row.odds});
        }
    }
    return flat;
}

function weightedPick(rows) {
    const total = rows.reduce((s, r) => s + r.odds, 0);
    let r = Math.random() * total;
    for (const row of rows) {
        r -= row.odds;
        if (r <= 0) return row;
    }
    return rows[rows.length - 1];
}

async function randomEncounter() {
    if (spawnTable === null) spawnTable = await loadSpawns();
    const pick = weightedPick(spawnTable);
    addItem(pick.pokedex_id, pick.level, Math.random() > 0.5);
}

const ws = new WebSocket(`ws://${location.host}/ws`);
const chat = document.getElementById("chat");
const timer = document.getElementById("timer")

const audioPlayer = document.getElementById("music");
audioPlayer.volume = 0.05;

// Pokemon.Gender enum values from pc/src/Pokemon.py: UNKNOWN=1, MALE=2, FEMALE=3.
// addItem expects gender as: true=male, false=female, null=unknown.
function genderFromValue(v) {
    if (v === 2) return true;
    if (v === 3) return false;
    return null;
}

ws.onmessage = (event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch { return; }
    if (msg.type === "encounter") {
        addItem(msg.pokedex_id, msg.level ?? "?", genderFromValue(msg.gender), !!msg.is_shiny);
    }
};

function sendMessage() {
    const input = document.getElementById("msg");
    ws.send(input.value);
    input.value = "";
}

function clearEncounterRun() {
    if (encounters === 0) {
        console.log("Nothing to clear.");
        return;
    }
    encounters = 0;
    countDownDate = new Date().getTime();
    // save some timestamp to a runs table for this location
    // when i load new data I will only select encounters newer than the last runs timestamp (if there is one)
    // TODO: build an index on time for encounters
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

fillTable([
    // Pokemon Tower 3F
    {
        pokedex_id: 92,
        name: "Gastly",
        types: ["ghost", "poison"],
        levels: [
            {lv: 13, m: 330, f: 340},
            {lv: 14, m: 313, f: 332},
            {lv: 15, m: 341, f: 309},
            {lv: 16, m: 329, f: 340},
            {lv: 17, m: 310, f: 324},
            {lv: 18, m: 335, f: 317},
            {lv: 19, m: 318, f: 319},
        ]
    },
    {
        pokedex_id: 104,
        name: "Cubone",
        types: ["ground"],
        levels: [
            {lv: 15, m: 77, f: 79},
            {lv: 16, m: 82, f: 81},
            {lv: 17, m: 75, f: 71},
        ]
    },
    {
        pokedex_id: 93,
        name: "Haunter",
        types: ["ghost", "poison"],
        levels: [
            {lv: 20, m: 25, f: 26},
        ]
    },
]);

function fillTable(pokemons) {
    for (let pokemon of pokemons) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        const rowspan = pokemon.levels.length == 1 ? 2 : pokemon.levels.length + 2;
        td.setAttribute("rowspan", rowspan);
        tr.appendChild(td);
        const div = document.createElement("div");
        div.className = "pokemon";
        td.appendChild(div);
        const img = document.createElement("img");
        img.className = "sprite";
        img.src = `img/pokemon/${String(pokemon.pokedex_id).padStart(3, "0")}.png`;
        const p = document.createElement("p");
        p.innerText = pokemon.name
        div.appendChild(img)
        div.appendChild(p)
        const typesDiv = document.createElement("div");
        typesDiv.className = "types";
        div.appendChild(typesDiv)
        for (let type of pokemon.types) {
            const img = document.createElement("img");
            img.src = `img/types/${type}.png`;
            typesDiv.appendChild(img);
        }

        tbody.appendChild(tr)

        for (let level of pokemon.levels) {
            const tr = document.createElement("tr");
            const tdLevel = document.createElement("td");
            tdLevel.innerText = level.lv;
            const tdMales = document.createElement("td");
            tdMales.innerText = level.m;
            const tdFemales = document.createElement("td");
            tdFemales.innerText = level.f;
            const tdOdds = document.createElement("td");
            tdOdds.innerText = parseFloat((level.m + level.f) / encounters * 100).toFixed(2) + "%";
            tr.append(tdLevel, tdMales, tdFemales, tdOdds);
            tbody.appendChild(tr)
        }

        // Totals row only for pokemon with multiple levels
        const totalMales = 0;
        const totalFemales = 0;
        if (pokemon.levels.length > 1) {
            const trTotal = document.createElement("tr");
            const tdTotal = document.createElement("td");
            tdTotal.innerText = "Total";
            const tdMales = document.createElement("td");
            tdMales.innerText = totalMales;
            const tdFemales = document.createElement("td");
            tdFemales.innerText = totalFemales;
            const tdOdds = document.createElement("td");
            tdOdds.innerText = "50%";
            trTotal.append(tdTotal, tdMales, tdFemales, tdOdds);
            tbody.appendChild(trTotal)
        }
    }
}

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

function addItem(pokedexId, number, gender, isShiny = false) {
    pending.push([pokedexId, number, gender, isShiny]);
    drainPending();
}

function drainPending() {
    if (sliding || pending.length === 0) return;
    const [pokedexId, number, gender, isShiny] = pending.shift();
    encounters++;

    // Append the new (11th) slot off the right edge of the visible area.
    queue.appendChild(makeFilledSlot(pokedexId, number, gender, isShiny));
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

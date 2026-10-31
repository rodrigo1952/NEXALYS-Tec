/*
 * Horario del local por GRUPOS de días (Editar datos de mi tienda).
 *
 * - Cada grupo tiene sus días (botones Lun…Dom), la hora de abrir y cerrar y, si se marca,
 *   el refrigerio. Un día solo puede estar en un grupo: al marcarlo en otro, se mueve.
 * - «Agregar otro horario» suma un grupo (máximo 7); el tacho lo quita.
 * - Las horas se eligen de la lista (cada hora) o se escriben: «8:30 a. m.», «8.30 pm», «20:30».
 * - Abajo se ve un resumen en vivo de cómo lo verán los clientes.
 * Sin JavaScript el formulario funciona igual (el servidor revisa todo).
 */
(function () {
  "use strict";
  var contenedor = document.getElementById("grupos-horario");
  if (!contenedor) return;
  var plantilla = document.getElementById("plantilla-grupo");
  var total = document.getElementById("id_horario-TOTAL_FORMS");
  var botonAgregar = document.getElementById("agregar-grupo");
  var resumen = document.getElementById("resumen-horario");
  var DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
  var MAXIMO = 7;

  // ---- Horas ----
  function leerHora(texto) {
    var limpio = (texto || "").trim().toLowerCase().replace(/(\d)\.(\d)/g, "$1:$2")
      .replace(/\./g, "").replace(/\s/g, "").replace("hrs", "").replace("h", ":");
    if (!limpio) return null;
    var m = limpio.match(/^(\d{1,2})(?::(\d{2}))?:?(am|pm|a|p|m)?$/);
    if (!m) return { error: "Escríbela así: 8:00 a. m. o 8:30 p. m." };
    var h = parseInt(m[1], 10), min = parseInt(m[2] || "0", 10), p = m[3];
    if (min > 59) return { error: "Los minutos van de 00 a 59." };
    if (p) {
      if (h < 1 || h > 12) return { error: "Con a. m. o p. m. la hora va de 1 a 12." };
      if (p === "m") { if (h !== 12) return { error: "Agrega a. m. o p. m." }; return { minutos: 12 * 60 + min }; }
      if (p.charAt(0) === "a") return { minutos: (h === 12 ? 0 : h) * 60 + min };
      return { minutos: (h === 12 ? 12 : h + 12) * 60 + min };
    }
    if (h === 12 || h === 0 || (h >= 13 && h <= 23)) return { minutos: h * 60 + min };
    return { error: "¿De la mañana o de la noche? Agrega a. m. o p. m." };
  }
  function hora12(minutos) {
    var h = Math.floor(minutos / 60), m = minutos % 60;
    return (h % 12 || 12) + ":" + (m < 10 ? "0" : "") + m + " " + (h < 12 ? "a. m." : "p. m.");
  }

  // ---- Nombres de días: [0..5] -> «Lunes a sábado» (igual que en el servidor) ----
  function etiquetaDias(dias) {
    dias = dias.slice().sort(function (a, b) { return a - b; });
    if (dias.length === 7) return "Todos los días";
    var tramos = [];
    dias.forEach(function (d) {
      var ultimo = tramos[tramos.length - 1];
      if (ultimo && d === ultimo[ultimo.length - 1] + 1) ultimo.push(d); else tramos.push([d]);
    });
    var partes = [];
    tramos.forEach(function (t) {
      if (t.length >= 3) partes.push(DIAS[t[0]] + " a " + DIAS[t[t.length - 1]].toLowerCase());
      else t.forEach(function (d) { partes.push(DIAS[d]); });
    });
    partes = partes.map(function (p, i) { return i === 0 ? p : p.toLowerCase(); });
    return partes.length === 1 ? partes[0] : partes.slice(0, -1).join(", ") + " y " + partes[partes.length - 1];
  }

  function grupos() {
    return Array.prototype.filter.call(contenedor.querySelectorAll("[data-grupo]"), function (g) { return !g.hidden; });
  }
  function diasDe(grupo) {
    return Array.prototype.filter.call(grupo.querySelectorAll(".dia-chip__casilla"), function (c) { return c.checked; })
      .map(function (c) { return parseInt(c.value, 10); });
  }
  function campo(grupo, nombre) { return grupo.querySelector('[name$="-' + nombre + '"]'); }

  // ---- Resumen en vivo ----
  function actualizar() {
    var visibles = grupos();
    var porDia = {};
    visibles.forEach(function (grupo, indice) {
      grupo.querySelector("[data-numero-grupo]").textContent = indice + 1;
      var dias = diasDe(grupo);
      grupo.querySelector("[data-texto-dias]").textContent = dias.length ? "· " + etiquetaDias(dias) : "· sin días marcados";
      var abre = leerHora(campo(grupo, "abre").value), cierra = leerHora(campo(grupo, "cierra").value);
      if (!abre || !cierra || abre.error || cierra.error) return;
      var texto = hora12(abre.minutos) + " – " + hora12(cierra.minutos);
      if (campo(grupo, "con_refrigerio").checked) {
        var desde = leerHora(campo(grupo, "descanso_inicio").value), hasta = leerHora(campo(grupo, "descanso_fin").value);
        if (desde && hasta && !desde.error && !hasta.error) {
          texto = hora12(abre.minutos) + " – " + hora12(desde.minutos) + " y " + hora12(hasta.minutos) + " – " + hora12(cierra.minutos);
        }
      }
      dias.forEach(function (d) { porDia[d] = texto; });
    });
    var porTexto = {};
    for (var d = 0; d < 7; d++) {
      var texto = porDia[d] || "Cerrado";
      (porTexto[texto] = porTexto[texto] || []).push(d);
    }
    var filas = Object.keys(porTexto).map(function (t) { return { texto: t, dias: porTexto[t] }; });
    filas.sort(function (a, b) { return (a.texto === "Cerrado") - (b.texto === "Cerrado") || a.dias[0] - b.dias[0]; });
    resumen.innerHTML = "";
    filas.forEach(function (f) {
      var li = document.createElement("li");
      if (f.texto === "Cerrado") li.className = "cerrado";
      var dias = document.createElement("span");
      dias.textContent = etiquetaDias(f.dias);
      var horas = document.createElement("span");
      horas.textContent = f.texto.split(" y ").join("\n");  // mañana y tarde en líneas separadas
      li.append(dias, horas);
      resumen.appendChild(li);
    });
    botonAgregar.classList.toggle("d-none", visibles.length >= MAXIMO);
  }

  // ---- Comportamiento de cada grupo ----
  function preparar(grupo) {
    grupo.querySelectorAll(".dia-chip__casilla").forEach(function (casilla) {
      casilla.addEventListener("change", function () {
        if (casilla.checked) {
          // Un día solo puede estar en un horario: si estaba en otro, se mueve a este.
          grupos().forEach(function (otro) {
            if (otro === grupo) return;
            var igual = otro.querySelector('.dia-chip__casilla[value="' + casilla.value + '"]');
            if (igual && igual.checked) igual.checked = false;
          });
        }
        actualizar();
      });
    });
    var refrigerio = campo(grupo, "con_refrigerio");
    var cajaRefrigerio = grupo.querySelector("[data-refrigerio]");
    function mostrarRefrigerio() { cajaRefrigerio.hidden = !refrigerio.checked; }
    refrigerio.addEventListener("change", function () { mostrarRefrigerio(); actualizar(); });
    mostrarRefrigerio();

    grupo.querySelectorAll("[data-hora]").forEach(function (entrada) {
      entrada.addEventListener("input", actualizar);
      entrada.addEventListener("change", function () {
        var leida = leerHora(entrada.value);
        entrada.classList.toggle("is-invalid", Boolean(leida && leida.error));
        entrada.title = leida && leida.error ? leida.error : "";
        if (leida && !leida.error) entrada.value = hora12(leida.minutos);  // se ve siempre igual: «8:30 a. m.»
        actualizar();
      });
    });

    grupo.querySelector("[data-quitar-grupo]").addEventListener("click", function () {
      if (grupos().length === 1) {
        // Si es el único, se vacía (todos los días quedan cerrados).
        grupo.querySelectorAll(".dia-chip__casilla").forEach(function (c) { c.checked = false; });
        grupo.querySelectorAll("[data-hora]").forEach(function (e) { e.value = ""; });
        refrigerio.checked = false;
        mostrarRefrigerio();
      } else {
        var borrar = grupo.querySelector('[name$="-DELETE"]');
        if (borrar) borrar.checked = true;
        grupo.hidden = true;
      }
      actualizar();
    });
  }

  botonAgregar.addEventListener("click", function () {
    var indice = parseInt(total.value, 10);
    var html = plantilla.innerHTML.replace(/__prefix__/g, indice).replace(/__numero__/g, grupos().length + 1);
    var caja = document.createElement("div");
    caja.innerHTML = html.trim();
    var nuevo = caja.firstElementChild;
    contenedor.appendChild(nuevo);
    total.value = indice + 1;
    // Se marcan solos los días que todavía no tienen horario.
    var usados = {};
    grupos().forEach(function (g) { if (g !== nuevo) diasDe(g).forEach(function (d) { usados[d] = true; }); });
    nuevo.querySelectorAll(".dia-chip__casilla").forEach(function (c) { c.checked = !usados[c.value]; });
    preparar(nuevo);
    actualizar();
    campo(nuevo, "abre").focus();
  });

  contenedor.querySelectorAll("[data-grupo]").forEach(preparar);
  actualizar();
})();

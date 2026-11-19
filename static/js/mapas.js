/*
 * Mapas de NEXALYS Tec con OpenStreetMap (librería Leaflet, se carga desde cdnjs).
 *
 *   [data-mapa-tiendas]  «Tiendas cercanas»: todas las tiendas en el mapa y una lista que se ordena
 *                        por distancia cuando la persona comparte su ubicación.
 *   [data-mapa-editar]   «Editar datos de mi tienda»: la tienda pone el pin en su local.
 *   [data-mapa-tienda]   Perfil de una tienda: mapa pequeño con su local.
 *
 * Al marcar el local hay además:
 *   - «Mapa / Satélite»: fotos satelitales de Esri (World Imagery) con las calles encima.
 *   - «Buscar»: busca una calle o lugar de Quillabamba en OpenStreetMap (servicio Nominatim). Una búsqueda
 *     por clic (sin autocompletar), como pide su política de uso; las respuestas se recuerdan en la página.
 *   - «Ampliar mapa»: el mapa ocupa toda la pantalla; «Reducir mapa» (arriba o en la esquina del mapa, o Esc)
 *     lo devuelve a su lugar.
 *   «Buscar» entiende «Jr.», «Av.», «Psje.»… y quita el número de puerta; si no encuentra nada, prueba solo
 *     con el nombre de la calle.
 *
 * Privacidad: la ubicación de la persona se usa SOLO aquí, en su navegador, para medir distancias.
 * No se envía al servidor ni se guarda. Lo que se escribe en «Buscar» va solo a OpenStreetMap.
 */
(function () {
  "use strict";
  var CUADROS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  var ATRIBUCION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>';
  var SATELITE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
  var CALLES = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}";
  var ATRIBUCION_SATELITE = "Imágenes &copy; Esri, Maxar, Earthstar Geographics y la comunidad GIS";
  var BUSCADOR = "https://nominatim.openstreetmap.org/search";
  var MENSAJES = {
    seguro: "Tu navegador solo comparte la ubicación en páginas seguras (https).",
    permiso: "No diste permiso para usar tu ubicación. Puedes activarlo tocando el candado junto a la dirección de la página.",
    falla: "No se pudo obtener tu ubicación. Revisa que el GPS o la ubicación estén activados e inténtalo otra vez.",
  };

  function escapar(texto) {
    var div = document.createElement("div");
    div.textContent = texto == null ? "" : String(texto);
    return div.innerHTML;
  }

  function crearMapa(elemento, centro, zoom) {
    var mapa = L.map(elemento, { scrollWheelZoom: false }).setView(centro, zoom);
    mapa.capaCalles = L.tileLayer(CUADROS, {
      maxZoom: 19,
      attribution: ATRIBUCION,
      // OpenStreetMap pide saber desde qué sitio se usa el mapa (solo el dominio).
      referrerPolicy: "strict-origin-when-cross-origin",
    }).addTo(mapa);
    // La rueda del mouse solo hace zoom después de tocar el mapa (así no estorba al bajar por la página).
    mapa.on("click focus", function () { mapa.scrollWheelZoom.enable(); });
    mapa.on("mouseout", function () { mapa.scrollWheelZoom.disable(); });
    return mapa;
  }

  function sinMapa(elemento) {
    elemento.innerHTML = '<div class="mapa__aviso"><i class="bi bi-wifi-off" aria-hidden="true"></i>' +
      "<span>No se pudo cargar el mapa. Revisa tu conexión a internet y recarga la página.</span></div>";
  }

  // Pin con el logo (o la inicial) de la tienda.
  function pinTienda(tienda) {
    var dentro = tienda.logo ? '<img src="' + escapar(tienda.logo) + '" alt="">' : escapar(tienda.inicial);
    return L.divIcon({
      className: "pin-tienda",
      html: '<span class="pin-tienda__circulo">' + dentro + "</span>",
      iconSize: [44, 54],
      iconAnchor: [22, 52],
      popupAnchor: [0, -46],
    });
  }

  // Distancia en línea recta entre dos puntos [lat, lng], en metros (fórmula del haversine).
  function distancia(a, b) {
    var R = 6371000, rad = Math.PI / 180;
    var dLat = (b[0] - a[0]) * rad, dLng = (b[1] - a[1]) * rad;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a[0] * rad) * Math.cos(b[0] * rad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function textoDistancia(metros) {
    if (metros < 1000) return "a " + Math.max(10, Math.round(metros / 10) * 10) + " m";
    return "a " + (metros / 1000).toFixed(1).replace(".", ",") + " km";
  }

  function pedirUbicacion(exito, error) {
    if (!window.isSecureContext || !navigator.geolocation) { error("seguro"); return; }
    navigator.geolocation.getCurrentPosition(
      function (posicion) { exito([posicion.coords.latitude, posicion.coords.longitude], posicion.coords.accuracy); },
      function (problema) { error(problema.code === 1 ? "permiso" : "falla"); },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
    );
  }

  // ---------- Mapa / Satélite ----------
  function botonesCapas(mapa) {
    var satelite = L.layerGroup([
      L.tileLayer(SATELITE, { maxZoom: 19, maxNativeZoom: 18, attribution: ATRIBUCION_SATELITE }),
      L.tileLayer(CALLES, { maxZoom: 19, maxNativeZoom: 18 }),
    ]);
    var Control = L.Control.extend({
      options: { position: "topright" },
      onAdd: function () {
        var caja = L.DomUtil.create("div", "capas-mapa leaflet-bar");
        caja.setAttribute("role", "group");
        caja.setAttribute("aria-label", "Tipo de mapa");
        [["calles", "bi-map", "Mapa"], ["satelite", "bi-globe-americas", "Satélite"]].forEach(function (d) {
          var b = L.DomUtil.create("button", "capas-mapa__boton", caja);
          b.type = "button";
          b.dataset.capa = d[0];
          b.innerHTML = '<i class="bi ' + d[1] + '" aria-hidden="true"></i> ' + d[2];
          b.setAttribute("aria-pressed", d[0] === "calles" ? "true" : "false");
        });
        L.DomEvent.disableClickPropagation(caja);
        L.DomEvent.on(caja, "click", function (evento) {
          var boton = evento.target.closest("[data-capa]");
          if (!boton) return;
          var verSatelite = boton.dataset.capa === "satelite";
          if (verSatelite) { mapa.removeLayer(mapa.capaCalles); satelite.addTo(mapa); }
          else { mapa.removeLayer(satelite); mapa.capaCalles.addTo(mapa); }
          caja.querySelectorAll("[data-capa]").forEach(function (b) {
            b.setAttribute("aria-pressed", b === boton ? "true" : "false");
          });
        });
        return caja;
      },
    });
    new Control().addTo(mapa);
  }

  // ---------- Buscar una calle o lugar (OpenStreetMap / Nominatim) ----------
  // OpenStreetMap no entiende las abreviaturas de las direcciones peruanas ni los números de puerta:
  // «Jr. Vilcabamba N° 438» se busca como «jirón vilcabamba».
  var ABREVIATURAS = [
    [/\bjr\b\.?/g, "jirón"], [/\bjiron\b/g, "jirón"], [/\bav(da)?\b\.?/g, "avenida"],
    [/\b(psje|pje|pj|pasj)\b\.?/g, "pasaje"], [/\bca\b\.?/g, "calle"], [/\bclle\b\.?/g, "calle"],
    [/\bprol\b\.?/g, "prolongación"], [/\burb\b\.?/g, "urbanización"], [/\bcarr\b\.?/g, "carretera"],
    [/\bmalec\b\.?/g, "malecón"], [/\bpza\b\.?/g, "plaza"],
  ];
  var TIPOS_DE_VIA = /^(jirón|avenida|pasaje|calle|prolongación|urbanización|carretera|malecón|plaza)\s+/;

  function textoParaBuscar(texto) {
    var t = " " + texto.toLowerCase() + " ";
    // Número de puerta, manzana y lote: «N° 438», «nro. 12», «#5», «Mz. B Lt. 4», «s/n».
    t = t.replace(/(\b(n[°º]|nro\.?|no\.|num\.?)|#)\s*\d+[a-z]?/g, " ")
         .replace(/\b(mz|lt|lote|manzana)\b\.?\s*[a-z0-9-]+/g, " ")
         .replace(/\bs\/n\b/g, " ")
         .replace(/\s\d+[a-z]?\s*$/, " ");  // número al final («Jr. Espinar 438»); «Av. 25 de Julio» queda igual
    ABREVIATURAS.forEach(function (par) { t = t.replace(par[0], par[1]); });
    return t.replace(/[,;]+/g, " ").replace(/\s+/g, " ").trim();
  }
  function sinTipoDeVia(texto) {
    return texto.replace(TIPOS_DE_VIA, "").trim();
  }
  function buscadorDeDirecciones(mapa, centro, alElegir) {
    var campo = document.querySelector("[data-buscar-direccion]");
    var boton = document.querySelector("[data-buscar-boton]");
    var caja = document.querySelector("[data-resultados-busqueda]");
    if (!campo || !boton || !caja) return;
    var recordadas = {};
    var esperando = false;

    function avisar(clase, texto) {
      caja.innerHTML = "";
      var p = document.createElement("p");
      p.className = "small mb-2 " + clase;
      p.textContent = texto;
      caja.appendChild(p);
    }
    function ir(lugar) {
      var punto = [parseFloat(lugar.lat), parseFloat(lugar.lon)];
      mapa.setView(punto, lugar.type === "house" || lugar.addresstype === "building" ? 19 : 18);
      avisar("text-success", "Te llevamos a «" + lugar.name_corto + "». Ahora toca la puerta de tu local en el mapa para poner el pin.");
      alElegir();
    }
    function mostrar(lugares) {
      if (!lugares.length) {
        avisar("text-warning-emphasis", "No encontramos ese lugar en Quillabamba. Prueba solo con el nombre de la calle (ej. «Espinar») o mueve el mapa tú mismo.");
        return;
      }
      lugares.forEach(function (l) { l.name_corto = l.name || l.display_name.split(",")[0]; });
      if (lugares.length === 1) { ir(lugares[0]); return; }
      caja.innerHTML = '<p class="small mb-1 text-muted">Elige el lugar correcto:</p>';
      var lista = document.createElement("div");
      lista.className = "editor-ubicacion__opciones";
      lugares.forEach(function (lugar) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "btn btn-sm btn-outline-secondary";
        b.textContent = lugar.display_name.split(",").slice(0, 3).join(",");
        b.addEventListener("click", function () { ir(lugar); });
        lista.appendChild(b);
      });
      caja.appendChild(lista);
    }
    function consultar(texto) {
      if (recordadas[texto]) return Promise.resolve(recordadas[texto]);
      var d = 0.08;  // unos 9 km alrededor del centro de Quillabamba
      var url = BUSCADOR + "?" + new URLSearchParams({
        q: texto, format: "jsonv2", limit: "5", countrycodes: "pe", "accept-language": "es", bounded: "1",
        viewbox: [centro[1] - d, centro[0] + d, centro[1] + d, centro[0] - d].join(","),
      });
      return fetch(url, { referrerPolicy: "strict-origin-when-cross-origin", headers: { Accept: "application/json" } })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (lugares) { recordadas[texto] = lugares; return lugares; });
    }
    function esperar(ms) { return new Promise(function (listo) { setTimeout(listo, ms); }); }

    function buscar() {
      var escrito = campo.value.trim();
      if (escrito.length < 3) { avisar("text-muted", "Escribe al menos 3 letras."); return; }
      if (esperando) return;
      var arreglado = textoParaBuscar(escrito);
      var soloNombre = sinTipoDeVia(arreglado);
      esperando = true;
      boton.disabled = true;
      avisar("text-muted", "Buscando…");
      consultar(arreglado)
        .then(function (lugares) {
          // «Jirón Vilcabamba» no aparece, pero «Vilcabamba» sí: se intenta solo con el nombre,
          // un segundo después (máximo una búsqueda por segundo, política de uso de OpenStreetMap).
          if (lugares.length || !soloNombre || soloNombre === arreglado || soloNombre.length < 3) return lugares;
          return (recordadas[soloNombre] ? Promise.resolve() : esperar(1100)).then(function () { return consultar(soloNombre); });
        })
        .then(mostrar)
        .catch(function () { avisar("text-danger", "No se pudo buscar ahora. Revisa tu conexión o mueve el mapa tú mismo."); })
        .then(function () {
          setTimeout(function () { esperando = false; boton.disabled = false; }, 1100);
        });
    }
    boton.addEventListener("click", buscar);
    // Enter busca (y no envía el formulario de la página).
    campo.addEventListener("keydown", function (evento) {
      if (evento.key === "Enter") { evento.preventDefault(); buscar(); }
    });
  }

  // ---------- «Ampliar mapa» (pantalla completa dentro de la página) ----------
  function mapaAmpliable(mapa) {
    var editor = document.querySelector("[data-editor-ubicacion]");
    var ampliar = document.querySelector("[data-ampliar-mapa]");
    var cerrar = document.querySelector("[data-cerrar-mapa]");
    if (!editor || !ampliar || !cerrar) return;
    // Botón ⤢ / ⤡ en la esquina del mapa, debajo del + y el −, como en Google Maps.
    var enElMapa = null;
    var Control = L.Control.extend({
      options: { position: "topleft" },
      onAdd: function () {
        var caja = L.DomUtil.create("div", "leaflet-bar");
        enElMapa = L.DomUtil.create("a", "boton-ampliar-mapa", caja);
        enElMapa.href = "#";
        enElMapa.setAttribute("role", "button");
        L.DomEvent.disableClickPropagation(caja);
        L.DomEvent.on(enElMapa, "click", function (evento) {
          L.DomEvent.preventDefault(evento);
          cambiar(!editor.classList.contains("editor-ubicacion--ampliado"));
        });
        pintarBoton(false);
        return caja;
      },
    });
    function pintarBoton(abierto) {
      if (!enElMapa) return;
      var texto = abierto ? "Reducir mapa" : "Ampliar mapa";
      enElMapa.innerHTML = '<i class="bi ' + (abierto ? "bi-fullscreen-exit" : "bi-arrows-fullscreen") + '" aria-hidden="true"></i>';
      enElMapa.title = texto;
      enElMapa.setAttribute("aria-label", texto);
    }
    // El vidrio del diseño celeste (backdrop-filter en .tarjeta-cuenta) encierra a lo que tiene «position: fixed»:
    // el mapa ampliado quedaba atrapado dentro de su tarjeta y la página se congelaba. Por eso, al ampliarlo,
    // el editor se lleva directo a <body>, y al reducirlo vuelve a su lugar (marcado con un comentario).
    var lugar = null;
    function moverEditor(abrir) {
      if (abrir && !lugar) {
        lugar = document.createComment(" lugar del mapa ");
        editor.parentNode.insertBefore(lugar, editor);
        document.body.appendChild(editor);
      } else if (!abrir && lugar) {
        lugar.parentNode.insertBefore(editor, lugar);
        lugar.parentNode.removeChild(lugar);
        lugar = null;
      }
    }
    function cambiar(abrir) {
      moverEditor(abrir);
      pintarBoton(abrir);
      editor.classList.toggle("editor-ubicacion--ampliado", abrir);
      document.body.classList.toggle("mapa-ampliado-abierto", abrir);
      if (abrir) {
        editor.setAttribute("role", "dialog");
        editor.setAttribute("aria-label", "Mapa ampliado para marcar tu local");
      } else {
        editor.removeAttribute("role");
        editor.removeAttribute("aria-label");
      }
      setTimeout(function () { mapa.invalidateSize(); }, 50);
      (abrir ? cerrar : ampliar).focus();
    }
    new Control().addTo(mapa);
    ampliar.addEventListener("click", function () { cambiar(true); });
    cerrar.addEventListener("click", function () { cambiar(false); });
    document.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape" && editor.classList.contains("editor-ubicacion--ampliado")) cambiar(false);
    });
  }

  function centroDe(elemento) {
    return [parseFloat(elemento.dataset.centroLat), parseFloat(elemento.dataset.centroLng)];
  }

  // =================== Tiendas cercanas ===================
  function tiendasCercanas(elemento) {
    var tiendas = JSON.parse(document.getElementById("datos-tiendas").textContent || "[]");
    var lista = document.querySelector("[data-lista-tiendas]");
    var boton = document.querySelector("[data-mi-ubicacion]");
    var estado = document.querySelector("[data-estado-ubicacion]");
    var mapa = null, marcadores = {}, yo = null;

    if (window.L) {
      mapa = crearMapa(elemento, centroDe(elemento), 15);
      var puntos = [];
      tiendas.forEach(function (tienda) {
        if (tienda.lat === null) return;
        var punto = [tienda.lat, tienda.lng];
        puntos.push(punto);
        var estadoLocal = tienda.estado
          ? '<div class="small ' + (tienda.abierto ? "text-success" : "text-danger") + '">' + escapar(tienda.estado) + "</div>" : "";
        marcadores[tienda.id] = L.marker(punto, { icon: pinTienda(tienda), title: tienda.nombre, alt: tienda.nombre })
          .addTo(mapa)
          .bindPopup(
            '<div class="popup-tienda"><strong>' + escapar(tienda.nombre) + "</strong>" +
            '<div class="small text-muted">' + escapar(tienda.direccion) + "</div>" + estadoLocal +
            '<div class="popup-tienda__botones">' +
            '<a class="btn btn-sm btn-primary" target="_blank" rel="noopener" href="' + escapar(tienda.como_llegar) + '">Cómo llegar</a>' +
            '<a class="btn btn-sm btn-outline-primary" href="' + escapar(tienda.perfil) + '">Ver tienda</a></div></div>'
          );
      });
      if (puntos.length > 1) mapa.fitBounds(puntos, { padding: [40, 40], maxZoom: 17 });
      else if (puntos.length === 1) mapa.setView(puntos[0], 17);
    } else {
      sinMapa(elemento);
    }

    // «Ver en el mapa» de cada tienda de la lista.
    lista.querySelectorAll("[data-ver-en-mapa]").forEach(function (enlace) {
      enlace.addEventListener("click", function (evento) {
        var marcador = marcadores[enlace.dataset.verEnMapa];
        if (!mapa || !marcador) return;
        evento.preventDefault();
        mapa.setView(marcador.getLatLng(), 18);
        marcador.openPopup();
        if (elemento.getBoundingClientRect().top < 0 || window.innerWidth < 992) {
          elemento.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      });
    });

    if (!boton) return;
    boton.addEventListener("click", function () {
      boton.disabled = true;
      estado.className = "small text-muted";
      estado.textContent = "Buscando tu ubicación…";
      pedirUbicacion(function (aqui, precision) {
        boton.disabled = false;
        boton.innerHTML = '<i class="bi bi-crosshair" aria-hidden="true"></i> Actualizar mi ubicación';
        // Distancia a cada tienda y lista ordenada de la más cercana a la más lejana.
        var conDistancia = [];
        tiendas.forEach(function (tienda) {
          var item = lista.querySelector('[data-tienda="' + tienda.id + '"]');
          if (!item) return;
          var caja = item.querySelector("[data-distancia]");
          if (tienda.lat === null) { caja.classList.add("d-none"); return; }
          var metros = distancia(aqui, [tienda.lat, tienda.lng]);
          caja.textContent = textoDistancia(metros);
          caja.classList.remove("d-none");
          conDistancia.push({ item: item, metros: metros });
        });
        conDistancia.sort(function (a, b) { return a.metros - b.metros; });
        var primeroSinUbicacion = lista.querySelector("[data-sin-ubicacion]");
        conDistancia.forEach(function (fila) { lista.insertBefore(fila.item, primeroSinUbicacion); });
        estado.className = "small text-success";
        estado.textContent = conDistancia.length
          ? "Listo: las tiendas están ordenadas de la más cercana a la más lejana (distancias en línea recta)."
          : "Listo, pero ninguna tienda marcó todavía su ubicación en el mapa.";
        if (precision > 1000) estado.textContent += " Tu ubicación es aproximada (en una PC suele serlo).";
        if (!mapa) return;
        if (yo) mapa.removeLayer(yo);
        yo = L.circleMarker(aqui, { radius: 9, color: "#fff", weight: 3, fillColor: "#1A73E8", fillOpacity: 1 })
          .addTo(mapa).bindTooltip("Estás aquí", { permanent: false, direction: "top" });
        var cercanas = conDistancia.slice(0, 3).map(function (fila) {
          return marcadores[fila.item.dataset.tienda].getLatLng();
        });
        mapa.fitBounds([aqui].concat(cercanas), { padding: [50, 50], maxZoom: 17 });
      }, function (motivo) {
        boton.disabled = false;
        estado.className = "small text-danger";
        estado.textContent = MENSAJES[motivo];
      });
    });
    // Desde el Inicio («Usar mi ubicación», ?ubicacion=1): se pide la ubicación al llegar.
    if (new URLSearchParams(location.search).get("ubicacion") === "1") boton.click();
  }

  // =================== Ubicación del local (Editar datos) ===================
  function editarUbicacion(elemento) {
    var latitud = document.getElementById(elemento.dataset.latitud);
    var longitud = document.getElementById(elemento.dataset.longitud);
    var texto = document.querySelector("[data-coordenadas]");
    var botonUsar = document.querySelector("[data-usar-ubicacion]");
    var botonQuitar = document.querySelector("[data-quitar-ubicacion]");
    var avisoUbicacion = document.querySelector("[data-aviso-ubicacion]");
    if (!window.L) { sinMapa(elemento); if (botonUsar) botonUsar.disabled = true; return; }

    var inicial = latitud.value && longitud.value ? [parseFloat(latitud.value), parseFloat(longitud.value)] : null;
    // La ubicación que ya está guardada (si el formulario volvió con errores, «inicial» puede ser otra).
    var guardada = "guardadaLat" in elemento.dataset
      ? (elemento.dataset.guardadaLat && elemento.dataset.guardadaLng
        ? [parseFloat(elemento.dataset.guardadaLat), parseFloat(elemento.dataset.guardadaLng)] : null)
      : inicial;
    var mapa = crearMapa(elemento, inicial || centroDe(elemento), inicial ? 18 : 15);
    var pin = null;

    function mismoLugar(a, b) {
      if (!a || !b) return !a && !b;
      var la = a.lat !== undefined ? [a.lat, a.lng] : a, lb = b.lat !== undefined ? [b.lat, b.lng] : b;
      return la[0].toFixed(6) === lb[0].toFixed(6) && la[1].toFixed(6) === lb[1].toFixed(6);
    }
    // Un toque en el mapa mueve el pin: si quedó distinto de lo guardado, se avisa y se puede deshacer.
    function mostrar() {
      var actual = pin ? pin.getLatLng() : null;
      var cambio = !mismoLugar(actual, guardada);
      var deshacer = ' <button type="button" class="aviso-pin__deshacer" data-deshacer-pin>' +
        '<i class="bi bi-arrow-counterclockwise" aria-hidden="true"></i> Deshacer</button>';
      texto.classList.toggle("aviso-pin", cambio);
      if (cambio && actual && guardada) {
        texto.innerHTML = '<i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i> ' +
          "<span><strong>Moviste el pin.</strong> Aún no se guarda: presiona «Guardar cambios» o, si fue sin querer, deshazlo.</span>" + deshacer;
      } else if (cambio && actual) {
        texto.innerHTML = '<i class="bi bi-geo-alt-fill" aria-hidden="true"></i> ' +
          "<span><strong>Pin puesto en " + actual.lat.toFixed(6) + ", " + actual.lng.toFixed(6) + ".</strong> " +
          "Se guardará al presionar «Guardar cambios».</span>" + deshacer;
      } else if (cambio) {
        texto.innerHTML = '<i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i> ' +
          "<span><strong>Quitaste tu local del mapa.</strong> Aún no se guarda: presiona «Guardar cambios» o deshazlo.</span>" + deshacer;
      } else if (actual) {
        texto.innerHTML = '<i class="bi bi-geo-alt-fill text-success" aria-hidden="true"></i> ' +
          "Tu local está marcado aquí. Para moverlo, arrastra el pin o toca otro lugar del mapa.";
      } else {
        texto.innerHTML = '<i class="bi bi-info-circle" aria-hidden="true"></i> Aún no marcaste tu local: toca el mapa en el lugar de tu tienda.';
      }
      botonQuitar.classList.toggle("d-none", !pin);
    }
    function guardarCampos() {
      if (pin) {
        var p = pin.getLatLng();
        latitud.value = p.lat.toFixed(6);
        longitud.value = p.lng.toFixed(6);
      } else {
        latitud.value = "";
        longitud.value = "";
      }
      mostrar();
      // Avisa al formulario (static/js/formularios.js): la ubicación pide la contraseña.
      latitud.dispatchEvent(new Event("change", { bubbles: true }));
    }
    function crearPin(punto) {
      pin = L.marker(punto, { draggable: true, autoPan: true, title: "Tu local (arrástralo para ajustarlo)" }).addTo(mapa);
      pin.on("dragend", guardarCampos);
    }
    function ponerPin(punto) {
      if (pin) pin.setLatLng(punto);
      else crearPin(punto);
      guardarCampos();
    }

    if (inicial) crearPin(inicial);
    texto.addEventListener("click", function (evento) {
      if (!evento.target.closest("[data-deshacer-pin]")) return;
      if (guardada) {
        if (pin) pin.setLatLng(guardada); else crearPin(guardada);
        mapa.setView(guardada, Math.max(mapa.getZoom(), 17));
      } else if (pin) {
        mapa.removeLayer(pin);
        pin = null;
      }
      guardarCampos();
    });
    mostrar();
    mapa.on("click", function (evento) { ponerPin(evento.latlng); });
    botonesCapas(mapa);
    mapaAmpliable(mapa);
    buscadorDeDirecciones(mapa, centroDe(elemento), function () { mapa.scrollWheelZoom.enable(); });

    botonQuitar.addEventListener("click", function () {
      if (pin) { mapa.removeLayer(pin); pin = null; }
      guardarCampos();
    });
    botonUsar.addEventListener("click", function () {
      botonUsar.disabled = true;
      avisoUbicacion.className = "small text-muted";
      avisoUbicacion.textContent = "Buscando tu ubicación…";
      pedirUbicacion(function (aqui, precision) {
        botonUsar.disabled = false;
        ponerPin(aqui);
        mapa.setView(aqui, 18);
        avisoUbicacion.className = "small " + (precision > 100 ? "text-warning-emphasis" : "text-success");
        avisoUbicacion.textContent = precision > 100
          ? "Ubicación aproximada (± " + Math.round(precision) + " m). Arrastra el pin hasta la puerta de tu local."
          : "Listo. Revisa que el pin esté en tu local; si no, arrástralo.";
      }, function (motivo) {
        botonUsar.disabled = false;
        avisoUbicacion.className = "small text-danger";
        avisoUbicacion.textContent = MENSAJES[motivo];
      });
    });
    // El mapa está dentro de una tarjeta: se recalcula su tamaño cuando ya se ve.
    setTimeout(function () { mapa.invalidateSize(); }, 200);
  }

  // =================== Mapa pequeño en el perfil de la tienda ===================
  function mapaTienda(elemento) {
    if (!window.L) { sinMapa(elemento); return; }
    var punto = [parseFloat(elemento.dataset.lat), parseFloat(elemento.dataset.lng)];
    var mapa = crearMapa(elemento, punto, 17);
    L.marker(punto, {
      icon: pinTienda({ logo: elemento.dataset.logo, inicial: elemento.dataset.inicial }),
      title: elemento.dataset.nombre, alt: elemento.dataset.nombre,
    }).addTo(mapa);
  }

  var cercanas = document.querySelector("[data-mapa-tiendas]");
  if (cercanas) tiendasCercanas(cercanas);
  var editor = document.querySelector("[data-mapa-editar]");
  if (editor) editarUbicacion(editor);
  var perfil = document.querySelector("[data-mapa-tienda]");
  if (perfil) mapaTienda(perfil);
})();

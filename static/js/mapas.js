/*
 * Mapas de NEXALYS Tec con OpenStreetMap (librería Leaflet, se carga desde cdnjs).
 *
 *   [data-mapa-tiendas]  «Tiendas cercanas»: todas las tiendas en el mapa y una lista que se ordena
 *                        por distancia cuando la persona comparte su ubicación.
 *   [data-mapa-editar]   «Editar datos de mi tienda»: la tienda pone el pin en su local.
 *   [data-mapa-tienda]   Perfil de una tienda: mapa pequeño con su local.
 *
 * Privacidad: la ubicación de la persona se usa SOLO aquí, en su navegador, para medir distancias.
 * No se envía al servidor ni se guarda.
 */
(function () {
  "use strict";
  var CUADROS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  var ATRIBUCION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>';
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
    L.tileLayer(CUADROS, {
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
    var mapa = crearMapa(elemento, inicial || centroDe(elemento), inicial ? 18 : 15);
    var pin = null;

    function mostrar() {
      if (pin) {
        var p = pin.getLatLng();
        texto.innerHTML = '<i class="bi bi-geo-alt-fill text-success" aria-hidden="true"></i> Pin puesto en ' +
          p.lat.toFixed(6) + ", " + p.lng.toFixed(6) + ". Se guardará al presionar «Guardar cambios».";
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
    }
    function ponerPin(punto) {
      if (pin) pin.setLatLng(punto);
      else {
        pin = L.marker(punto, { draggable: true, autoPan: true, title: "Tu local (arrástralo para ajustarlo)" }).addTo(mapa);
        pin.on("dragend", guardarCampos);
      }
      guardarCampos();
    }

    if (inicial) {
      pin = L.marker(inicial, { draggable: true, autoPan: true, title: "Tu local (arrástralo para ajustarlo)" }).addTo(mapa);
      pin.on("dragend", guardarCampos);
    }
    mostrar();
    mapa.on("click", function (evento) { ponerPin(evento.latlng); });

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

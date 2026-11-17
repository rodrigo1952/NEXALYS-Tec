/*
 * Panel «Compartir» e «Imprimir y descargar» de «Código QR de tu tienda» (templates/tiendas/qr_cartel.html).
 *
 * Dibuja el cartel (logo, nombre, «Mira nuestros productos…», el QR, «Escanéame…» y NEXALYS Tec) en una
 * imagen PNG de 1080 × 1350 (formato vertical que WhatsApp, Facebook e Instagram muestran completo).
 * Botones [data-compartir-red]:
 *   whatsapp   celular: menú del teléfono con la imagen.  PC: copia la imagen y abre WhatsApp Web (o la app,
 *              si así lo eligió en static/js/whatsapp.js) para pegarla con Ctrl + V en el chat.
 *   facebook   celular: menú del teléfono.  PC: abre Facebook para publicar el enlace (con vista previa) y deja
 *              la imagen copiada por si se prefiere pegarla.
 *   instagram  celular: menú del teléfono.  PC: descarga la imagen y abre instagram.com («Crear»).
 *   sistema    «Más opciones»: menú del sistema con la imagen; si el navegador no puede, la ventana de
 *              compartir el enlace (static/js/compartir.js).
 *   copiar     copia el enlace.   descargar   descarga la imagen.
 * Ninguna página puede adjuntar archivos en WhatsApp Web, Facebook o Instagram: por eso se copia o se descarga.
 * Todo se hace en el navegador: la imagen no se sube a ningún lado.
 */
(function () {
  "use strict";
  var panel = document.querySelector("[data-panel-cartel]");
  var cartel = document.querySelector(".cartel-qr");
  var aviso = document.querySelector("[data-aviso-cartel]");
  if (!panel || !cartel) return;

  var ANCHO = 1080, ALTO = 1350;
  var AZUL = "#0B1B3A", CIAN = "#19C3E6", CIAN_TEXTO = "#0A6F89", GRIS = "#46566D";
  var LETRA = '"Space Grotesk", system-ui, sans-serif';
  var archivoListo = null;

  function cargarImagen(src) {
    return new Promise(function (listo, fallo) {
      var img = new Image();
      img.onload = function () { listo(img); };
      img.onerror = fallo;
      img.src = src;
    });
  }

  function lineas(ctx, texto, anchoMax) {
    var palabras = texto.split(" "), resultado = [], actual = "";
    palabras.forEach(function (p) {
      var prueba = actual ? actual + " " + p : p;
      if (ctx.measureText(prueba).width > anchoMax && actual) { resultado.push(actual); actual = p; }
      else actual = prueba;
    });
    if (actual) resultado.push(actual);
    return resultado;
  }

  function redondeado(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function dibujar() {
    var svg = cartel.querySelector(".cartel-qr__codigo svg");
    var logo = cartel.querySelector("img.cartel-qr__logo");
    var nombre = cartel.querySelector(".cartel-qr__nombre").textContent.trim();
    var llamado = cartel.querySelector(".cartel-qr__llamado").textContent.trim();
    var enlace = cartel.querySelector(".cartel-qr__enlace").textContent.trim();
    var inicial = (nombre[0] || "?").toUpperCase();

    var copia = svg.cloneNode(true);
    copia.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    copia.setAttribute("width", "720");
    copia.setAttribute("height", "720");
    var urlQr = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(copia));

    return Promise.all([
      cargarImagen(urlQr),
      logo ? cargarImagen(logo.currentSrc || logo.src).catch(function () { return null; }) : Promise.resolve(null),
      document.fonts ? document.fonts.ready : Promise.resolve(),
    ]).then(function (r) {
      var qr = r[0], imgLogo = r[1];
      var lienzo = document.createElement("canvas");
      lienzo.width = ANCHO;
      lienzo.height = ALTO;
      var ctx = lienzo.getContext("2d");
      ctx.fillStyle = "#F3F6FA";
      ctx.fillRect(0, 0, ANCHO, ALTO);
      redondeado(ctx, 40, 40, ANCHO - 80, ALTO - 80, 48);
      ctx.fillStyle = "#FFFFFF";
      ctx.fill();
      ctx.lineWidth = 8;
      ctx.strokeStyle = AZUL;
      ctx.stroke();
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";

      // Logo (o inicial) y nombre de la tienda.
      var y = 110, radio = 64, cx = ANCHO / 2;
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, y + radio, radio, 0, Math.PI * 2);
      ctx.closePath();
      if (imgLogo) {
        ctx.clip();
        ctx.fillStyle = "#FFFFFF";
        ctx.fillRect(cx - radio, y, radio * 2, radio * 2);
        var lado = Math.min(imgLogo.naturalWidth, imgLogo.naturalHeight);
        ctx.drawImage(imgLogo, (imgLogo.naturalWidth - lado) / 2, (imgLogo.naturalHeight - lado) / 2, lado, lado,
                      cx - radio, y, radio * 2, radio * 2);
      } else {
        ctx.fillStyle = AZUL;
        ctx.fill();
        ctx.fillStyle = "#FFFFFF";
        ctx.font = "700 64px " + LETRA;
        ctx.fillText(inicial, cx, y + radio + 22);
      }
      ctx.restore();
      y += radio * 2 + 70;
      ctx.fillStyle = AZUL;
      ctx.font = "700 64px " + LETRA;
      lineas(ctx, nombre, ANCHO - 200).slice(0, 2).forEach(function (l) { ctx.fillText(l, cx, y); y += 72; });

      // Llamado, QR e instrucción.
      ctx.font = "600 38px " + LETRA;
      ctx.fillStyle = "#1F2937";
      y += 10;
      lineas(ctx, llamado, ANCHO - 200).forEach(function (l) { ctx.fillText(l, cx, y); y += 46; });
      var ladoQr = Math.min(620, ALTO - y - 260);
      ctx.drawImage(qr, cx - ladoQr / 2, y, ladoQr, ladoQr);
      y += ladoQr + 56;
      ctx.fillStyle = CIAN_TEXTO;
      ctx.font = "700 36px " + LETRA;
      ctx.fillText("Escanéame con la cámara de tu celular", cx, y);
      y += 44;
      ctx.fillStyle = GRIS;
      ctx.font = "400 26px " + LETRA;
      ctx.fillText(enlace, cx, y);

      // Marca al pie.
      ctx.font = "700 34px " + LETRA;
      var marca = "NEXALYS ", tec = "Tec.";
      var anchoMarca = ctx.measureText(marca + tec).width;
      var x0 = cx - anchoMarca / 2;
      ctx.textAlign = "left";
      ctx.fillStyle = AZUL;
      ctx.fillText(marca, x0, ALTO - 90);
      ctx.fillStyle = CIAN;
      ctx.fillText(tec, x0 + ctx.measureText(marca).width, ALTO - 90);

      return new Promise(function (listo) { lienzo.toBlob(listo, "image/png"); });
    }).then(function (blob) {
      var nombreArchivo = "cartel-" + (panel.dataset.archivo || "tienda") + ".png";
      return new File([blob], nombreArchivo, { type: "image/png" });
    });
  }

  function decir(texto, clase) {
    if (!aviso) return;
    aviso.className = "panel-cartel__aviso " + (clase || "text-muted");
    aviso.textContent = texto;
  }

  function descargar(archivo) {
    var url = URL.createObjectURL(archivo);
    var a = document.createElement("a");
    a.href = url;
    a.download = archivo.name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  function esComputadora() {
    var ua = navigator.userAgent || "";
    if (navigator.userAgentData && navigator.userAgentData.mobile) return false;
    if (/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle/i.test(ua)) return false;
    if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) return false;
    return window.matchMedia ? window.matchMedia("(pointer: fine)").matches : true;
  }
  function puedeCompartirImagen(archivo) {
    return !!(navigator.canShare && navigator.canShare({ files: [archivo] }));
  }
  function compartirConElSistema(archivo) {
    return navigator.share({ files: [archivo], title: panel.dataset.titulo, text: panel.dataset.texto })
      .catch(function (error) { if (!error || error.name !== "AbortError") throw error; });  // AbortError: cerró el menú
  }
  function copiarImagen(archivo) {
    if (!navigator.clipboard || !window.ClipboardItem) return Promise.reject(new Error("sin portapapeles"));
    return navigator.clipboard.write([new ClipboardItem({ "image/png": archivo })]);
  }
  function abrir(url) {
    if (url.indexOf("whatsapp://") === 0) { window.location.href = url; return; }  // la app de WhatsApp, sin pestaña
    window.open(url, "_blank", "noopener");
  }
  function modoWhatsApp() {
    try { return localStorage.getItem("nexalys_whatsapp_modo"); } catch (e) { return null; }
  }

  // La imagen se prepara apenas carga la página: el navegador solo deja abrir el menú de compartir,
  // copiar o abrir otra pestaña justo después del clic, así que no se puede esperar a dibujarla.
  var preparada = null;
  function preparar() {
    if (!preparada) preparada = dibujar().catch(function (e) { preparada = null; throw e; });
    return preparada;
  }
  window.addEventListener("load", function () { preparar().catch(function () { /* se reintenta al hacer clic */ }); });

  var ACCIONES = {
    whatsapp: function (archivo) {
      if (!esComputadora() && puedeCompartirImagen(archivo)) return compartirConElSistema(archivo);
      var texto = encodeURIComponent(panel.dataset.texto);
      var url = modoWhatsApp() === "app" ? "whatsapp://send?text=" + texto : "https://web.whatsapp.com/send?text=" + texto;
      return copiarImagen(archivo).then(function () {
        abrir(url);
        decir("Imagen copiada. En WhatsApp elige el chat y pega la imagen con Ctrl + V (el enlace ya va escrito).", "text-success");
      }, function () {
        descargar(archivo);
        abrir(url);
        decir("Descargamos «" + archivo.name + "». En WhatsApp elige el chat y adjúntala con el clip 📎.", "text-success");
      });
    },
    facebook: function (archivo) {
      if (!esComputadora() && puedeCompartirImagen(archivo)) return compartirConElSistema(archivo);
      var url = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(panel.dataset.url);
      return copiarImagen(archivo).then(function () {
        abrir(url);
        decir("Se abrió Facebook con el enlace de tu tienda. Si prefieres publicar el cartel, ya está copiado: pégalo con Ctrl + V.", "text-success");
      }, function () {
        abrir(url);
        decir("Se abrió Facebook con el enlace de tu tienda.", "text-success");
      });
    },
    instagram: function (archivo) {
      if (!esComputadora() && puedeCompartirImagen(archivo)) return compartirConElSistema(archivo);
      descargar(archivo);
      abrir("https://www.instagram.com/");
      decir("Descargamos «" + archivo.name + "». En Instagram toca «Crear» y elige esa imagen. Desde el celular es más fácil: el botón Instagram abre el menú del teléfono.", "text-success");
      return null;
    },
    sistema: function (archivo, boton) {
      if (puedeCompartirImagen(archivo)) return compartirConElSistema(archivo);
      boton.dataset.compartirListo = "1";  // este navegador no puede: la ventana de compartir el enlace
      boton.click();
      return null;
    },
    copiar: function () {
      var enlace = panel.dataset.url;
      return (navigator.clipboard ? navigator.clipboard.writeText(enlace) : Promise.reject())
        .then(function () { decir("Enlace copiado: " + enlace, "text-success"); },
              function () { decir("Copia este enlace: " + enlace, "text-muted"); });
    },
    descargar: function (archivo) {
      descargar(archivo);
      decir("Descargamos «" + archivo.name + "».", "text-success");
      return null;
    },
  };

  panel.addEventListener("click", function (evento) {
    var boton = evento.target.closest("[data-compartir-red]");
    if (!boton) return;
    if (boton.dataset.compartirListo) { delete boton.dataset.compartirListo; return; }  // lo abre compartir.js
    evento.preventDefault();
    evento.stopPropagation();  // que compartir.js no abra su ventana (en «Más opciones» decide este script)
    var accion = ACCIONES[boton.dataset.compartirRed];
    if (!accion) return;
    if (!archivoListo) decir("Preparando la imagen…");
    (archivoListo ? Promise.resolve(archivoListo) : preparar())
      .then(function (archivo) {
        archivoListo = archivo;
        if (aviso && aviso.textContent === "Preparando la imagen…") decir("");
        return accion(archivo, boton);
      })
      .catch(function () { decir("No se pudo compartir la imagen. Usa «Descargar cartel» o «Copiar enlace».", "text-danger"); });
  });

  // Para pruebas.
  window.NexalysCartel = { dibujar: dibujar };
})();

# Librerías de terceros (dentro del proyecto)

Se copiaron aquí para no depender de otros sitios (CDN): la página funciona sin internet en el laboratorio,
el navegador no le envía la IP del visitante a terceros y la cabecera CSP solo permite archivos propios.
Los archivos son los mismos de npm (jsDelivr); solo se quitó la línea final `sourceMappingURL` (los mapas
para depurar no se incluyen y `collectstatic` fallaría al no encontrarlos).

| Carpeta | Librería | Versión | Licencia |
|---|---|---|---|
| bootstrap/ | Bootstrap (CSS y JS con Popper) | 5.3.3 | MIT |
| bootstrap-icons/ | Bootstrap Icons | 1.11.3 | MIT |
| chartjs/ | Chart.js (gráficos) | 4.4.1 | MIT |
| leaflet/ | Leaflet (mapas) | 1.9.4 | BSD-2 |
| fuentes/ | Space Grotesk (variable) y Lilita One, de Fontsource | 5.x | SIL OFL 1.1 |

Para actualizar una librería: descargar la versión nueva con `Claude outputs/descargar_librerias.ps1`
(cambiando el número), quitar la línea `sourceMappingURL` y correr las pruebas.

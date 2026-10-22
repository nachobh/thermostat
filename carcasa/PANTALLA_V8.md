# v8 (preliminar): sin tapa frontal, pantalla pegada sobre las paredes – 2026-10-21

## Idea
Quitar la tapa y el marco: la pantalla DWIN 5,7" (144,8 × 110,2 × 18,9 mm, supuesta) se **pega sobre el borde superior de las paredes** (cinta VHB o similar) y queda enrasada con el contorno de la caja. Las paredes (2,5 mm) llevan una pestaña interior de 4 × 1,5 mm que aumenta la superficie de pegado a 6,5 mm. Solo se ve la pantalla.

## Consecuencia: la huella baja, la profundidad sube
Con la huella igual al contorno de la pantalla (interior 139,8 × 105,2 mm) ya no cabe la columna lateral de la v7 (PCB 100 + 49,5 mm) y hay que apilar:
1. **Capa 1 (z < 25):** PCB a la izquierda; a la derecha NodeMCU (vertical, invertido, USB abajo) y DHT22 con deflector.
2. **Capa 2:** cubierta de 230 V sobre la PCB (z 25–48,5): bandeja, tabique derecho, mini-placa, 3 relés y tapa propia. La PCB queda debajo, sin 230 V.

| Versión | Huella | Profundidad total | Volumen | Pantalla activa |
|---|---|---|---|---|
| v7 (con tapa) | 161 × 122 | 49,8 | 978 cm³ | 100 cm² |
| v7 sin tapa (solo quitar la tapa) | 161 × 122 | 47,3 | 929 cm³ | 100 cm² (queda un escalón de 8 mm alrededor) |
| **v8 (enrasada)** | **144,8 × 110,2** | **68,9** (carcasa 50 + pantalla 18,9) | **1099 cm³** | **100 cm²** |

v8 gana 28 % de huella pero es ~ 20 mm más profunda. Si pesa más la profundidad que la huella, la v7 sin tapa es la alternativa.

## Puntos delicados
- **Fijación:** solo adhesivo. Con una pantalla táctil que se pulsa, la pestaña debe estar bien apoyada y limpia; usar cinta de espuma acrílica de ≥ 1 mm. Añadir tornillos a través de los orificios de la propia pantalla cuando se conozcan (no están en los listados).
- **Cables de la pantalla:** su conector queda en la cara trasera dentro de la carcasa; falta el plano para decidir por dónde sale el mazo (de momento hay 2 pasos de cable Ø12 en la pared izquierda para la parte de 230 V).
- **Calor y mantenimiento:** la pantalla es la tapa; para abrir hay que despegarla. Hacer primero las pruebas en banco (ver `checklist.md`).
- Siguen válidos los avisos de `PANTALLA_V7.md`: variante UART TTL 3,3 V (no RS232), plano mecánico, consumo, cargador ≥ 2 A.

## Archivos
`render_v8*.png`, `render_v8.html`, `esquema_v8.png`, `stl_v8/` (+ `visor_stl_v8.html`): carcasa, cubierta de 230 V y tapa de la cubierta; estancas y sin interferencias con PCB + componentes, NodeMCU (placa, ESP-12, USB, regletas, conectores), DHT22, pantalla, mini-placa, relés y bornas.

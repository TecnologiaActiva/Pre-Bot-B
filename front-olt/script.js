const API = "http://127.0.0.1:5000"

const tituloChat = document.getElementById("tituloChat")
const chatStatus = document.getElementById("chatStatus")
const chatAvatar = document.getElementById("chatAvatar")
const uploadForm = document.getElementById("uploadForm")
const fileInput = document.getElementById("fileInput")
const listaChats = document.getElementById("listaChats")
const mensajesDiv = document.getElementById("mensajes")

// Variable para rastrear el primer usuario (para diferenciar mensajes)
let primerUsuario = null

/* =========================
   SUBIR VARIOS CHATS
========================= */
fileInput.addEventListener("change", async () => {
  const archivos = fileInput.files
  if (!archivos.length) return

  // Mostrar estado de carga
  listaChats.innerHTML = `<li class="loader">Subiendo ${archivos.length} archivo(s)...</li>`

  for (const archivo of archivos) {
    const formData = new FormData()
    formData.append("file", archivo)

    await fetch(`${API}/procesar`, {
      method: "POST",
      body: formData,
    })
  }

  fileInput.value = ""
  await cargarChats()
})

/* =========================
   OBTENER INICIAL
========================= */
function getInitial(nombre) {
  if (!nombre) return "?"
  return nombre.charAt(0).toUpperCase()
}

/* =========================
   CARGAR LISTADO DE CHATS
========================= */
async function cargarChats() {
  listaChats.innerHTML = `<li class="loader">Cargando chats...</li>`

  try {
    const resp = await fetch(`${API}/chats`)
    const chats = await resp.json()

    listaChats.innerHTML = ""

    if (!Array.isArray(chats) || chats.length === 0) {
      listaChats.innerHTML = `<li class="empty-state">No hay chats cargados</li>`
      return
    }

    chats.forEach((chat) => {
      const li = document.createElement("li")
      li.innerHTML = `
                <div class="avatar">${getInitial(chat.Nombre)}</div>
                <div class="chat-preview">
                    <div class="chat-name">${chat.Nombre}</div>
                    <div class="chat-date">${chat.FechaCarga}</div>
                </div>
            `

      li.addEventListener("click", () => {
        document.querySelectorAll("#listaChats li").forEach((el) => el.classList.remove("activo"))
        li.classList.add("activo")
        cargarMensajes(chat.id, chat.Nombre)
      })

      listaChats.appendChild(li)
    })
  } catch (err) {
    console.error(err)
    listaChats.innerHTML = `<li class="empty-state">No se pudo conectar al backend</li>`
  }
}

/* =========================
   CARGAR MENSAJES DE UN CHAT
========================= */
async function cargarMensajes(chatId, nombreChat) {
  if (!chatId) {
    mensajesDiv.innerHTML = `<div class="mensajes-vacio">Chat inválido</div>`
    return
  }

  // Actualizar header
  tituloChat.textContent = nombreChat
  chatAvatar.textContent = getInitial(nombreChat)
  chatStatus.textContent = "Cargando..."

  mensajesDiv.innerHTML = `<div class="loader">Cargando mensajes...</div>`

  try {
    const resp = await fetch(`${API}/mensajes/${chatId}`)
    const mensajes = await resp.json()

    mensajesDiv.innerHTML = ""

    if (!Array.isArray(mensajes) || mensajes.length === 0) {
      mensajesDiv.innerHTML = `<div class="mensajes-vacio">No hay mensajes en este chat</div>`
      chatStatus.textContent = "Sin mensajes"
      return
    }

    // Detectar el primer usuario para diferenciar mensajes
    primerUsuario = mensajes[0]?.usuario || null

    mensajes.forEach((msg) => {
      const div = document.createElement("div")
      div.className = "mensaje"

      // Si es el primer usuario, marcarlo como "propio"
      if (msg.usuario === primerUsuario) {
        div.classList.add("propio")
      }

      div.innerHTML = `
                <div class="msg-header">
                    <span class="msg-user">${msg.usuario}</span>
                    <span class="msg-time">${msg.fecha} ${msg.hora}</span>
                </div>
                <div class="msg-text">${msg.mensaje}</div>
            `
      mensajesDiv.appendChild(div)
    })

    mensajesDiv.scrollTop = mensajesDiv.scrollHeight
    chatStatus.textContent = `${mensajes.length} mensajes`
  } catch (err) {
    console.error(err)
    mensajesDiv.innerHTML = `<div class="mensajes-vacio">Error cargando mensajes</div>`
    chatStatus.textContent = "Error"
  }
}

/* =========================
   INIT
========================= */
cargarChats()

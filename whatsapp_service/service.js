import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';

const FASTAPI_ENDPOINT = 'http://127.0.0.1:8000/api/observations/raw';

async function startWhatsAppBridge() {
  // Store authentication credentials locally in ./auth_info
  const { state, saveCreds } = await useMultiFileAuthState('auth_info');

  const sock = makeWASocket({
    auth: state,
    logger: pino({ level: 'silent' }), // Suppress internal socket logs
    printQRInTerminal: false,
    markOnlineOnConnect: false, // Prevents setting your status to online constantly
  });

  // 1. Connection & QR Handling
  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('\n--- SCAN THIS QR CODE WITH WHATSAPP LINKED DEVICES ---');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'close') {
      const statusCode = (lastDisconnect?.error)?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log(`Connection closed. Status: ${statusCode}. Reconnecting: ${shouldReconnect}`);
      if (shouldReconnect) {
        startWhatsAppBridge();
      } else {
        console.log('Logged out. Delete the auth_info folder and restart to re-pair.');
      }
    } else if (connection === 'open') {
      console.log('✅ WhatsApp Bridge connected successfully to Life OS!');
    }
  });

  // Save session credentials whenever updated
  sock.ev.on('creds.update', saveCreds);

  // 2. Message Upsert Listener
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    // Only process new incoming/outgoing messages
    if (type !== 'notify') return;

    for (const msg of messages) {
      try {
        const jid = msg.key.remoteJid;

        // Skip status stories and broadcasts
        if (!jid || jid.endsWith('@broadcast')) continue;

        // Extract message body across different text payload types
        const body =
          msg.message?.conversation ||
          msg.message?.extendedTextMessage?.text ||
          msg.message?.imageMessage?.caption ||
          msg.message?.videoMessage?.caption ||
          null;

        if (!body || body.trim().length < 5) continue;

        const isGroup = jid.endsWith('@g.us');
        const sender = msg.pushName || (msg.key.fromMe ? 'Me' : jid.split('@')[0]);
        const messageId = msg.key.id;

        const observationPayload = {
          source: 'chat',
          channel: 'WhatsApp',
          sender: sender,
          raw_text: body.trim(),
          metadata: {
            message_id: messageId,
            chat_id: jid,
            is_group: isGroup,
            from_me: Boolean(msg.key.fromMe),
            timestamp: msg.messageTimestamp,
          },
        };
        console.log(observationPayload);
        // Forward to FastAPI ingestion endpoint
        const response = await fetch(FASTAPI_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(observationPayload),
        });

        if (response.ok) {
          console.log(`[FORWARDED] ${sender}: "${body.slice(0, 45)}..."`);
        } else {
          console.error(`[FASTAPI ERROR] Status ${response.status}`);
        }
      } catch (err) {
        console.error('Error processing message item:', err.cause || err.message);
      }
    }
  });
}

startWhatsAppBridge();
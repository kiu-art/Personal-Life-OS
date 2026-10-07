import 'package:flutter/material.dart';
import '../models/ambient_state.dart';
import '../services/app_permissions.dart';
import '../services/backend_service.dart';

class SettingsScreen extends StatefulWidget {
  final AmbientState ambientState;
  final Function(AmbientState updatedState) onStateChanged;

  const SettingsScreen({
    super.key,
    required this.ambientState,
    required this.onStateChanged,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _gmailController;
  late TextEditingController _backendUrlController;
  late bool _gmailSync;
  late bool _whatsAppBridge;
  late List<String> _selectedLanguages;
  String _syncFeedback = '';
  String _connectionStatus = '';
  bool _isTestingBackend = false;

  final List<String> _rawStreamLogs = [
    '[AUDIO 08:15] "Bixy: I woke up late" -> /api/observations/voice-checkin',
    '[NOTIF 08:32] WhatsApp: Dev Group "Standup at 11:30" -> /api/observations/',
    '[AUDIO 08:42] Marathi: "Aai la call karaycha ahe" -> causal graph',
  ];

  final List<String> _availableLanguages = [
    'English',
    'Hindi',
    'Marathi',
    'Mix',
  ];

  @override
  void initState() {
    super.initState();
    _gmailController = TextEditingController(
        text: widget.ambientState.connectedGmail ?? 'user@gmail.com');
    _backendUrlController =
        TextEditingController(text: widget.ambientState.backendBaseUrl);
    _gmailSync = widget.ambientState.isGmailSyncEnabled;
    _whatsAppBridge = widget.ambientState.isWhatsAppBridgeEnabled;
    _selectedLanguages = List.from(widget.ambientState.activeLanguages);
    _testBackendConnection();
  }

  @override
  void dispose() {
    _gmailController.dispose();
    _backendUrlController.dispose();
    super.dispose();
  }

  Future<void> _testBackendConnection() async {
    setState(() {
      _isTestingBackend = true;
      _connectionStatus = 'Checking…';
    });
    final backend =
        BackendService(baseUrl: _backendUrlController.text.trim());
    final isOnline = await backend.checkHealth();
    if (mounted) {
      setState(() {
        _isTestingBackend = false;
        _connectionStatus =
            isOnline ? 'Online' : 'Unreachable — is port 8000 up?';
      });
    }
  }

  Future<void> _simulateNotification(
      String channel, String sender, String text) async {
    final backend =
        BackendService(baseUrl: _backendUrlController.text.trim());
    final now = DateTime.now();
    final timeStr =
        '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';

    final res = await backend.sendNotificationObservation(
      channel: channel,
      sender: sender,
      rawText: text,
      metadata: {
        'simulated_at': now.toIso8601String(),
        'client': 'Bixy_Mobile'
      },
    );

    if (mounted) {
      setState(() {
        _rawStreamLogs.insert(
          0,
          '[$channel $timeStr] $sender: "$text" -> ${res['status'] ?? 'queued'}',
        );
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Sent — ${res['status'] ?? 'queued'}')),
      );
    }
  }

  void _saveAndSync() {
    final updated = widget.ambientState.copyWith(
      connectedGmail: _gmailController.text.trim(),
      isGmailSyncEnabled: _gmailSync,
      isWhatsAppBridgeEnabled: _whatsAppBridge,
      activeLanguages: _selectedLanguages,
      backendBaseUrl: _backendUrlController.text.trim(),
    );
    widget.onStateChanged(updated);
    _testBackendConnection();
    setState(() {
      _syncFeedback = 'Synced to backend.';
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final online = _connectionStatus == 'Online';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          if (_syncFeedback.isNotEmpty)
            Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                leading: Icon(Icons.check_circle_rounded,
                    color: scheme.primary),
                title: Text(_syncFeedback),
                dense: true,
              ),
            ),

          // Gmail
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Column(
              children: [
                SwitchListTile(
                  secondary: const Icon(Icons.mail_outline_rounded),
                  title: const Text('Gmail'),
                  subtitle: const Text('Calendar + email tasks'),
                  value: _gmailSync,
                  onChanged: (val) => setState(() => _gmailSync = val),
                ),
                Padding(
                  padding:
                      const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: TextField(
                    controller: _gmailController,
                    style: theme.textTheme.bodyMedium,
                    decoration: const InputDecoration(
                      hintText: 'you@gmail.com',
                    ),
                  ),
                ),
              ],
            ),
          ),

          // WhatsApp listener
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Column(
              children: [
                SwitchListTile(
                  secondary:
                      const Icon(Icons.chat_bubble_outline_rounded),
                  title: const Text('WhatsApp'),
                  subtitle:
                      const Text('Chat notifications as raw text'),
                  value: _whatsAppBridge,
                  onChanged: (val) async {
                    if (val) {
                      final hasAccess =
                          await AppPermissions.hasListenerAccess();
                      if (!hasAccess) {
                        final granted =
                            await AppPermissions.requestListenerAccess();
                        if (!context.mounted) return;
                        if (!granted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text(
                                  'Listener access denied — WhatsApp stays off.'),
                            ),
                          );
                          return;
                        }
                      }
                    }
                    if (!mounted) return;
                    setState(() => _whatsAppBridge = val);
                  },
                ),
                Padding(
                  padding:
                      const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _whatsAppBridge
                              ? scheme.primary
                              : scheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _whatsAppBridge
                            ? 'Active • Permission granted'
                            : 'Off',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Languages
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Languages',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      )),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _availableLanguages.map((lang) {
                      return FilterChip(
                        label: Text(lang),
                        selected: _selectedLanguages.contains(lang),
                        onSelected: (val) {
                          setState(() {
                            if (val) {
                              _selectedLanguages.add(lang);
                            } else {
                              _selectedLanguages.remove(lang);
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ),

          // Raw stream
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Raw stream',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      )),
                  const SizedBox(height: 10),
                  Container(
                    height: 110,
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: scheme.surfaceContainerLowest,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: _rawStreamLogs.map((log) {
                          return Padding(
                            padding:
                                const EdgeInsets.only(bottom: 5),
                            child: Text(
                              log,
                              style: theme.textTheme.bodySmall?.copyWith(
                                fontFamily: 'monospace',
                                color: log.startsWith('[AUDIO]')
                                    ? scheme.primary
                                    : scheme.onSurfaceVariant,
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.tonal(
                          onPressed: () => _simulateNotification(
                            'WhatsApp',
                            'Dev Group',
                            'Standup moved to 11:30 on Meet',
                          ),
                          child: const Text('Test WhatsApp'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: FilledButton.tonal(
                          onPressed: () => _simulateNotification(
                            'Gmail',
                            'Calendar',
                            'Review draft due 15:00',
                          ),
                          child: const Text('Test Gmail'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Backend
          Card(
            margin: const EdgeInsets.only(bottom: 16),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Backend',
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          )),
                      TextButton(
                        onPressed: _isTestingBackend
                            ? null
                            : _testBackendConnection,
                        child: Text(
                            _isTestingBackend ? 'Checking…' : 'Ping'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  TextField(
                    controller: _backendUrlController,
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(fontFamily: 'monospace'),
                    decoration: const InputDecoration(
                      hintText: 'http://10.0.2.2:8000',
                    ),
                  ),
                  if (_connectionStatus.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: online
                                ? scheme.primary
                                : scheme.error,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _connectionStatus,
                          style:
                              theme.textTheme.bodySmall?.copyWith(
                            color: online
                                ? scheme.primary
                                : scheme.error,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),

          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _saveAndSync,
              child: const Text('Save & sync'),
            ),
          ),
        ],
      ),
    );
  }
}

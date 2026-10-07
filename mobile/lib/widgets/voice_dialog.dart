import 'package:flutter/material.dart';

class VoiceAssistantModal extends StatefulWidget {
  final Function(String voiceText) onCommandProcessed;

  const VoiceAssistantModal({
    super.key,
    required this.onCommandProcessed,
  });

  @override
  State<VoiceAssistantModal> createState() => _VoiceAssistantModalState();
}

class _VoiceAssistantModalState extends State<VoiceAssistantModal> {
  final TextEditingController _inputController = TextEditingController();
  String _detectedLanguage = 'Hinglish';

  final List<Map<String, String>> _sampleTriggers = [
    {'label': 'Woke up late', 'text': 'Bixy: I woke up late', 'lang': 'English'},
    {
      'label': 'Standup delay 30m',
      'text': 'Bixy: Dev standup thoda delay kardo 30 minutes',
      'lang': 'Hinglish'
    },
    {
      'label': 'Aai la call karaycha',
      'text': 'Bixy: Udya sakali Aai la call karaycha ahe',
      'lang': 'Marathi'
    },
  ];

  @override
  void initState() {
    super.initState();
    _inputController.text = 'Bixy: I woke up late';
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  void _submit(String text) {
    if (text.trim().isEmpty) return;
    widget.onCommandProcessed(text.trim());
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;

    return Container(
      padding: EdgeInsets.only(
        top: 12,
        left: 20,
        right: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 38,
              height: 4,
              decoration: BoxDecoration(
                color: scheme.onSurfaceVariant.withOpacity(0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Ask Bixy', style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  )),
              IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          Text(
            'Listening • $_detectedLanguage',
            style: theme.textTheme.bodySmall?.copyWith(
              color: scheme.primary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _inputController,
            style: theme.textTheme.bodyLarge,
            decoration: const InputDecoration(
              hintText: 'Say it like you mean it…',
            ),
            onSubmitted: _submit,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _sampleTriggers.map((trig) {
              return ActionChip(
                label: Text(trig['label']!),
                onPressed: () {
                  setState(() {
                    _inputController.text = trig['text']!;
                    _detectedLanguage = trig['lang']!;
                  });
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () => _submit(_inputController.text),
              icon: const Icon(Icons.auto_awesome_rounded, size: 18),
              label: const Text('Send to Bixy'),
            ),
          ),
        ],
      ),
    );
  }
}

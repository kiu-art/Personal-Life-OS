import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screens/home_container.dart';
import 'theme/bixy_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Immersive edge-to-edge system navigation & status bar
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: Color(0xFF0A0908),
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  runApp(const BixyApp());
}

class BixyApp extends StatelessWidget {
  const BixyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Bixy Life OS',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.dark,
      theme: BixyTheme.dark(),
      home: const HomeContainer(),
    );
  }
}

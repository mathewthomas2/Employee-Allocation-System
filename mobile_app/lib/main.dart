import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'login_page.dart';
import 'home_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final empId = prefs.getString('emp_id');
  
  runApp(MyApp(initialEmpId: empId));
}

class MyApp extends StatelessWidget {
  final String? initialEmpId;
  const MyApp({super.key, this.initialEmpId});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Supermarket Monitor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      // Auto-Login Logic:
      home: initialEmpId != null ? HomePage(empId: initialEmpId!) : const LoginPage(),
      routes: {
        '/login': (context) => const LoginPage(),
      },
    );
  }
}

import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class HomePage extends StatefulWidget {
  final String empId;
  const HomePage({super.key, required this.empId});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String status = "Connecting...";
  String? activeAlert;
  Timer? _timer;

  // IMPORTANT: For Android Emulator, use 10.0.2.2 instead of localhost
  // If running on physical device, use your PC's IP address (e.g., http://192.168.1.50:8000)
  final String baseUrl = "http://192.168.10.101:8000"; 

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _timer = Timer.periodic(const Duration(seconds: 2), (timer) {
      _checkNotifications();
    });
  }

  Future<void> _checkNotifications() async {
    try {
      // 1. Check Personal Notifications
      final response = await http.get(Uri.parse('$baseUrl/notifications/${widget.empId}'));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['has_notification'] == true) {
           setState(() {
             activeAlert = data['message'];
             status = "Action Required!";
           });
           _showAlertDialog(data['message']);
        } else {
           if (activeAlert == null) {
             setState(() {
               status = "Monitoring Zone...";
             });
           }
        }
      }
    } catch (e) {
      setState(() {
        status = "Connection Error (Check IP)";
      });
      print(e);
    }
  }

  void _showAlertDialog(String message) {
    // Only show if not already open? For simplicity, we just rely on the banner for now
    // or we can show a SnackBar
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("ALERT: $message"),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 5),
        action: SnackBarAction(label: "ACKNOWLEDGE", textColor: Colors.white, onPressed: () {
           setState(() {
             activeAlert = null;
             status = "Monitoring Zone...";
           });
        }),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    bool isAlert = activeAlert != null;

    return Scaffold(
      appBar: AppBar(
        title: Text("Employee: ${widget.empId}"),
        backgroundColor: isAlert ? Colors.red : Colors.deepPurple[100],
      ),
      backgroundColor: isAlert ? Colors.red[50] : Colors.white,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isAlert ? Icons.warning_amber_rounded : Icons.check_circle_outline,
              size: 100,
              color: isAlert ? Colors.red : Colors.green,
            ),
            const SizedBox(height: 20),
            Text(
              status,
              style: TextStyle(
                fontSize: 24, 
                fontWeight: FontWeight.bold,
                color: isAlert ? Colors.red : Colors.black87
              ),
              textAlign: TextAlign.center,
            ),
            if (activeAlert != null) ...[
               const SizedBox(height: 20),
               Container(
                 padding: const EdgeInsets.all(16),
                 margin: const EdgeInsets.symmetric(horizontal: 20),
                 decoration: BoxDecoration(
                   color: Colors.red[100],
                   borderRadius: BorderRadius.circular(10),
                   border: Border.all(color: Colors.red)
                 ),
                 child: Text(
                   activeAlert!,
                   style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                   textAlign: TextAlign.center,
                 ),
               ),
               const SizedBox(height: 30),
               ElevatedButton.icon(
                 onPressed: () {
                   setState(() {
                     activeAlert = null;
                     status = "Monitoring Zone...";
                   });
                 },
                 icon: const Icon(Icons.check),
                 label: const Text("Mark as Resolved"),
                 style: ElevatedButton.styleFrom(
                   backgroundColor: Colors.green,
                   foregroundColor: Colors.white,
                   padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                 ),
               )
            ]
          ],
        ),
      ),
    );
  }
}

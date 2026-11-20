import importlib.machinery
import sys
import unittest

# Pre-load enums module directly to avoid loading all DB models during unit test
enums_mod = importlib.machinery.SourceFileLoader(
    "apps.api.src.models.enums", "apps/api/src/models/enums.py"
).load_module()
sys.modules["apps.api.src.models.enums"] = enums_mod

from apps.api.src.models.enums import SymbolType
from apps.api.src.services.parser.universal_parser import (
    extract_universal_dependencies,
    extract_universal_symbols,
)


class TestUniversalParser(unittest.TestCase):
    def test_dart_flutter_symbol_and_import_extraction(self):
        dart_code = b"""
import 'package:flutter/material.dart';
import 'package:unotusk/services/api_service.dart';

class PaymentCheckoutWidget extends StatefulWidget {
  @override
  Widget build(BuildContext context) {
    return Container();
  }

  void processPayment() {
    print("Processing");
  }
}

enum PaymentStatus {
  pending,
  completed,
  failed,
}
"""
        symbols = extract_universal_symbols(dart_code, "Dart")
        # Verify class was extracted
        class_syms = [s for s in symbols if s.name == "PaymentCheckoutWidget"]
        self.assertEqual(len(class_syms), 1)
        self.assertEqual(class_syms[0].symbol_type, SymbolType.CLASS)

        # Verify child methods build and processPayment
        method_names = [m.name for m in class_syms[0].children]
        self.assertIn("build", method_names)
        self.assertIn("processPayment", method_names)

        # Verify enum
        enum_syms = [s for s in symbols if s.name == "PaymentStatus"]
        self.assertEqual(len(enum_syms), 1)
        self.assertEqual(enum_syms[0].symbol_type, SymbolType.ENUM)

        # Verify imports
        deps = extract_universal_dependencies(dart_code, "Dart")
        targets = [d.raw_target for d in deps]
        self.assertIn("package:flutter/material.dart", targets)
        self.assertIn("package:unotusk/services/api_service.dart", targets)

    def test_rust_symbol_and_import_extraction(self):
        rust_code = b"""
use std::sync::Arc;
use tokio::sync::Mutex;

pub struct TaskQueue {
  pub capacity: usize,
}

pub fn spawn_worker() {
  println!("Worker spawned");
}
"""
        symbols = extract_universal_symbols(rust_code, "Rust")
        struct_syms = [s for s in symbols if s.name == "TaskQueue"]
        self.assertEqual(len(struct_syms), 1)
        self.assertEqual(struct_syms[0].symbol_type, SymbolType.TYPE)

        fn_syms = [s for s in symbols if s.name == "spawn_worker"]
        self.assertEqual(len(fn_syms), 1)
        self.assertEqual(fn_syms[0].symbol_type, SymbolType.FUNCTION)

        deps = extract_universal_dependencies(rust_code, "Rust")
        targets = [d.raw_target for d in deps]
        self.assertIn("std::sync::Arc", targets)
        self.assertIn("tokio::sync::Mutex", targets)

    def test_java_interface_and_class_extraction(self):
        java_code = b"""
package com.acme.billing;

import java.util.List;
import com.acme.models.Invoice;

public interface InvoiceService {
  void generateInvoice();
}

public class StripeGateway implements InvoiceService {
  public void chargeCustomer() {
    // charge
  }
}
"""
        symbols = extract_universal_symbols(java_code, "Java")
        interface_syms = [s for s in symbols if s.name == "InvoiceService"]
        self.assertEqual(len(interface_syms), 1)
        self.assertEqual(interface_syms[0].symbol_type, SymbolType.INTERFACE)

        class_syms = [s for s in symbols if s.name == "StripeGateway"]
        self.assertEqual(len(class_syms), 1)
        self.assertEqual(class_syms[0].symbol_type, SymbolType.CLASS)


if __name__ == "__main__":
    unittest.main()

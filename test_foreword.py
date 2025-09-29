#!/usr/bin/env python3

from aim.news.models import Foreword, ForewordAuthor
from aim.frontend.pages.AIM_Premium import AIMPremiumEmailData
from aim.emailer.base import EmailBuilder
from dataclasses import asdict

def test_foreword_rendering():
    # Create test data
    test_data = AIMPremiumEmailData()
    test_data.foreword = Foreword(
        author=ForewordAuthor.Fiona,
        text='Dear Reader,\n\nThis is paragraph two.\n\nThis is paragraph three.'
    )

    print('=== Testing Foreword Data ===')
    print('Foreword text:', repr(test_data.foreword.text))
    print('Foreword paras:', test_data.foreword.paras)
    print('Number of paras:', len(test_data.foreword.paras))

    print('\n=== Testing Data Conversion ===')
    data_dict = asdict(test_data)
    print('Foreword in dict:', data_dict['foreword'])
    
    # Check if paras property gets included when converting to dict
    foreword_dict = data_dict['foreword']
    print('Keys in foreword dict:', list(foreword_dict.keys()))

    print('\n=== Testing Template Loading ===')
    try:
        email_builder = EmailBuilder.AIMPremium()
        print('Template loaded successfully!')
        
        # Test rendering with minimal data
        html = email_builder.render(test_data)
        print('Template rendered successfully!')
        print('HTML length:', len(html))
        
        # Check if foreword content is in the HTML
        if 'Dear Reader' in html:
            print('✓ Foreword text found in HTML')
        else:
            print('✗ Foreword text NOT found in HTML')
            
        if 'paragraph two' in html:
            print('✓ Second paragraph found in HTML')
        else:
            print('✗ Second paragraph NOT found in HTML')
            
        # Let's also check what's actually in the foreword section
        print('\n=== Checking HTML Content ===')
        import re
        # Look for foreword section
        foreword_match = re.search(r'<!-- FOREWORD BODY -->(.*?)<!-- SEPARATOR -->', html, re.DOTALL)
        if foreword_match:
            print('Foreword body section found:')
            print(foreword_match.group(1)[:500] + '...' if len(foreword_match.group(1)) > 500 else foreword_match.group(1))
        else:
            print('Foreword body section NOT found')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_foreword_rendering()

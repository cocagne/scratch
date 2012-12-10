#ifndef ABIDOS_BYTE_STRING_H
#define ABIDOS_BYTE_STRING_H

#include <string.h>
#include <iostream>

#include <boost/utility.hpp>

#include "abidos_common.hpp"

namespace abidos
{

class ByteString : public sg::ByteString
{
   uint8_t     * m_pdata;
   std::size_t   m_len;
   std::size_t   m_allocated;
   
  public:
   
   ByteString() : m_pdata(0), m_len(0), m_allocated(0)
   {
      std::cerr << " ### ByteString constructor: " << std::endl;
   }

   ~ByteString()
   {
      std::cerr << " ### Byte String destructor!!!" << std::endl;
      if ( m_pdata )
         delete [] m_pdata;
   }
      
   const uint8_t * data()   const { return m_pdata; }
   std::size_t     length() const { return m_len;   }
      
   void assign( const uint8_t * d, std::size_t nbytes )
   {
      if ( m_allocated < nbytes )
      {
         if ( m_pdata )
            delete [] m_pdata;

         m_pdata = new uint8_t[ nbytes ];
         m_allocated = nbytes;
      }

      memcpy(m_pdata, d, nbytes);
      m_len = nbytes;
   }
      
   void assign( const std::string & n )
   {
      assign( (const uint8_t *) n.data(), n.length() );
   }
      
   void assign( const char * nullTerminatedString )
   {
      assign( (const uint8_t *) nullTerminatedString, strlen(nullTerminatedString) + 1 );
   }

   bool operator< ( const sg::ByteString * rhs ) const
   {
      return *this < *static_cast<const ByteString*>(rhs);
   }

      
   bool operator==( const sg::ByteString * rhs ) const
   {
      return *this == *static_cast<const ByteString*>(rhs);
   }
      
   bool operator< ( const ByteString & rhs) const
   {
      return strncmp( (const char *) m_pdata, (const char *)rhs.m_pdata, m_len < rhs.m_len ? m_len : rhs.m_len ) < 0; 
   }
   bool operator==( const ByteString & rhs) const
   {
      return strncmp( (const char *) m_pdata, (const char *)rhs.m_pdata, m_len < rhs.m_len ? m_len : rhs.m_len ) == 0; 
   }
   bool operator==( const char * rhs ) const
   {
      int slen = strlen(rhs);
      return strncmp( (const char *) m_pdata, rhs, m_len < slen ? m_len : slen ) == 0; 
   }
};
   
   
} // end namespace abidos


#endif

